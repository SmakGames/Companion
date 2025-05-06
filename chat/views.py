import json
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.views import APIView
from .models import User, UserProfile, ChatHistory
from .serializers import UserSerializer, \
    UserProfileSerializer, UserProfileCreateSerializer, \
    ChatHistorySerializer, RegisterSerializer, PasswordChangeSerializer, \
    PasswordResetSerializer, SecurityAnswerSerializer
from openai import OpenAI, OpenAIError, APIConnectionError, RateLimitError
import requests
from . import config
from . import message_analyst as ma


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    # permission_classes = [IsAuthenticated]


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    # permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return UserProfileCreateSerializer
        return UserProfileSerializer

    def create(self, request, *args, **kwargs):
        serializer = UserProfileCreateSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegisterView(APIView):
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "User created"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetView(APIView):
    def post(self, request):
        # Rate limiting (e.g., 5 attempts per hour per IP)
        ip = request.META.get('REMOTE_ADDR')
        cache_key = f"password_reset_{ip}"
        attempts = cache.get(cache_key, 0)
        if attempts >= 5:
            return Response({"error": "Too many attempts. Try again later."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        serializer = PasswordResetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            cache.set(cache_key, attempts + 1, timeout=3600)
            return Response({"message": "Password reset successful."}, status=status.HTTP_200_OK)
        cache.set(cache_key, attempts + 1, timeout=3600)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Password changed successfully."}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SecurityAnswerView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        ip = request.META.get('REMOTE_ADDR')
        cache_key = f"security_answer_{ip}"
        attempts = cache.get(cache_key, 0)
        if attempts >= 5:
            return Response({"error": "Too many attempts. Try again later."}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        serializer = SecurityAnswerSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(request)
            cache.set(cache_key, attempts + 1, timeout=3600)
            return Response({"message": "Security answer updated."}, status=status.HTTP_200_OK)
        cache.set(cache_key, attempts + 1, timeout=3600)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChatHistoryViewSet(viewsets.ModelViewSet):
    queryset = ChatHistory.objects.all()
    serializer_class = ChatHistorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ChatHistory.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@api_view(['GET'])
# @permission_classes([IsAuthenticated])
def user_profile(request):
    profile = request.user.profile
    try:
        return Response({
            "username": request.user.username,
            "preferred_name": profile.preferred_name or request.user.username,
            "account_status": profile.account_status,
            "city": profile.city or "",
            "chat_history": [
                {"message": chat.message, "is_user": chat.is_user_message,
                    "time": chat.timestamp.isoformat()}
                for chat in request.user.chat_history.all()[:10]
            ]
        })
    except ObjectDoesNotExist:
        return Response({"error": "User does not have a profile"})


# @permission_classes([IsAuthenticated]) # not yet
@api_view(['GET'])
@csrf_exempt
@never_cache
def weather_api(request):
    try:
        # Use query parameters for GET
        lat = request.query_params.get("lat")
        lon = request.query_params.get("lon")
        units = request.query_params.get(
            "units", "imperial")  # Default to imperial

        # Validate lat and lon
        if not lat or not lon:
            return Response(
                {"error": "Latitude and longitude are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            lat = float(lat)
            lon = float(lon)
        except (TypeError, ValueError):
            return Response(
                {"error": "Invalid latitude or longitude format"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Weather API call
        weather_api_key = config.weather_api_key
        try:
            weather = requests.get(
                f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={weather_api_key}&units={units}"
            ).json()

            if weather.get("cod") != 200:
                print("COD line")
                return Response(
                    {"error": f"Weather API error: {weather.get('message', 'Unknown')}"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            temp = int(weather["main"]["temp"])
            print(f"The temp is {temp} degrees")
            city = weather["name"]
        except (requests.RequestException, KeyError, ValueError) as e:
            return Response(
                {"error": f"Failed to fetch weather: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response({
            "temperature": temp,
            "city": city,
            "units": units
        }, status=status.HTTP_200_OK)

    except (TypeError, ValueError, KeyError) as e:
        return Response(
            {"error": f"Invalid request: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST
        )


# def starts_with_question_word(message):
#    question_words = ("what", "when", "where", "how",
#                      "why", "who", "can", "do", "if")
#    return message.lower().startswith(question_words)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def talk_api(request):
    # Safely extract message and location data
    message = request.data.get("message")
    city = request.data.get("city")
    if not message:
        return Response({"error": "Message required"}, status=status.HTTP_400_BAD_REQUEST)
    print(f"The city is {city}")

    # Use authenticated user
    user = request.user

    # Save user message to ChatHistory
    try:
        ChatHistory.objects.create(
            user=user,
            message=message,
            is_user_message=True
        )
    except ValueError as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # Serialization
    serializer = UserSerializer(user)

    # Special responses
    if "help" in message.lower():
        response = "Uh oh. How can I help?"
        ChatHistory.objects.create(
            user=user,
            message=response,
            is_user_message=False
        )
        return Response({
            "reply": response,
            "message": "What can I do?",
            "user": serializer.data
        })

    if message.lower() == "hey":
        response = "Hey! What's up?"
        ChatHistory.objects.create(
            user=user,
            message=response,
            is_user_message=False
        )
        return Response({
            "reply": response,
            "user": serializer.data
        })

    # Determine response style
    if ma.starts_with_question_word(message):
        print("Message starts with a question word.")
        how_to_respond = "brevity"
    else:
        print("Message is a statement")
        how_to_respond = "gallows humor"

    # Fetch recent chat history (last 5 exchanges)
    recent_history = ChatHistory.objects.filter(
        user=user).order_by('-timestamp')[:5]
    # Reverse to chronological order for prompt
    recent_history = reversed(recent_history)

    # Construct OpenAI messages array
    messages = [
        {
            "role": "system",
            "content": (
                f"You are a friendly, empathetic roommate for an elderly person living in {city or 'an unspecified city'}. "
                "Respond warmly, naturally, and with {how_to_respond}. Keep responses concise (1-2 sentences) and appropriate for seniors. "
                "Use the conversation history to maintain context and refer to prior messages when relevant."
            )
        }
    ]
    # Add recent chat history
    for chat in recent_history:
        messages.append({
            "role": "user" if chat.is_user_message else "assistant",
            "content": chat.message
        })
    # Add current message
    messages.append({"role": "user", "content": message})

    # AI Response
    try:
        client = OpenAI(api_key=config.openai_api_key)
        ai_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=100,  # Limit response length
            temperature=0.7  # Balanced creativity
        ).choices[0].message.content

        # Save AI response to ChatHistory
        ChatHistory.objects.create(
            user=user,
            message=ai_response,
            is_user_message=False
        )

    except APIConnectionError as e:
        print("Connection error:", e)
        return Response({"reply": "Sorry, I had trouble connecting!"}, status=503)

    except RateLimitError as e:
        print("Rate limit reached:", e)
        return Response({"reply": "Too many chats right now—try again soon!"}, status=429)

    except OpenAIError as e:
        print("General OpenAI error:", e)
        return Response({"reply": "Something’s off with the AI!"}, status=500)

    except Exception as e:
        print("Unexpected error:", e)
        return Response({"reply": "Oops! Something unexpected happened."}, status=500)

    print(f"AI Response: {ai_response}")
    print(f"Serializer Data: {serializer.data}")
    print(f"Message: {message}")

    # Improved question detection
    is_question = ai_response.strip().endswith('?') or any(
        word in ai_response.lower() for word in ['what', 'when', 'where', 'how', 'why', 'who', 'can', 'do', 'if']
    )

    # Prepare response data
    response_data = {
        "response": ai_response,
        "user": serializer.data,
        "message": message,
        "is_question": is_question
    }
    print(f"Response JSON: {json.dumps(response_data)}")
    return Response(response_data)


@csrf_exempt
def talk(request):
    '''
    If you're building a simple web-based chat interface, "talk" is your guy.
    '''
    if request.method == "POST":
        message = request.POST.get("message", "").strip()
        lat = request.POST.get("my_lat").strip()
        lon = request.POST.get("my_lon").strip()
        user = request.user if request.user.is_authenticated else User.objects.get_or_create(
            username="Guest", defaults={"first_name": "Guest", "last_name": "User"}
        )[0]
        # user, _ = User.objects.get_or_create(
        #    username="BigMike", defaults={"first_name": "Test", "last_name": "User"}
        # )
        # weather support
        # Save user message
        ChatHistory.objects.create(
            user=user, message=message, is_user_message=True)

        weather_api_key = config.weather_api_key
        try:
            weather = requests.get(
                f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={weather_api_key}&units=imperial"
            ).json()
            temp = int(weather["main"]["temp"]) if weather.get(
                "main") and "temp" in weather["main"] else None
            city = weather["name"]
        except (requests.RequestException, KeyError):
            temp = "unknown"

        # AI Response
        # Get from openai.com
        try:
            client = OpenAI(
                api_key=config.openai_api_key)
            prompt = f"Act as a friendly companion for an elderly person. They said: '{message}'. It’s {temp}°F outside. Respond warmly and naturally."
            ai_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": prompt}]
            ).choices[0].message.content
            ChatHistory.objects.create(
                user=user, message=ai_response, is_user_message=False)
        except APIConnectionError as e:
            print("Connection error:", e)
            ai_response = "Sorry, I had trouble connecting to the AI service."

        except RateLimitError as e:
            print("Rate limit reached:", e)
            ai_response = "Sorry, I'm being asked too many questions right now. Please try again shortly."

        except OpenAIError as e:
            print("General OpenAI error:", e)
            ai_response = "Sorry, something went wrong with the AI service."

        except Exception as e:
            print("Unexpected error:", e)
            ai_response = "Oops! Something unexpected happened."

        # response = f"You said: {message}. I remember you, {user.first_name}! It is {temp} degrees today."
        user.last_chat = message
        user.save()

        # serialization
        serializer = UserSerializer(user)

        context = {
            "reply": ai_response,
            "user": serializer.data,
            "message": message,
            "temp": temp,
            "city": city,
        }
        return render(request, "chat/talk.html", context)

    return render(request, "chat/talk.html")
