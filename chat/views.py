from django.shortcuts import render
from django.http import HttpResponse
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import never_cache
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view
from .models import User, UserProfile
from .serializers import UserSerializer, UserProfileSerializer, UserProfileCreateSerializer
from openai import OpenAI, OpenAIError, APIConnectionError, RateLimitError
import requests
from . import config


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]


class UserProfileViewSet(viewsets.ModelViewSet):
    queryset = UserProfile.objects.all()
    permission_classes = [IsAuthenticated]

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


@api_view(['POST'])
@csrf_exempt
@never_cache
def talk_api(request):
    '''
    If you're integrating with a mobile app or external system, you'd use talk_api.

    @api_view(['POST']): This is a DRF (Django Rest Framework) decorator 
    indicating that the view only accepts POST requests.

    @csrf_exempt: Disables CSRF protection (common in API endpoints).
    '''

    # Safely extract message and location data
    message = request.data.get("message")
    city = request.data.get("city")
    print(f"The city is {city}")

    # look up the user
    user, _ = User.objects.get_or_create(
        user_name="TestUser", defaults={"first_name": "Test", "last_name": "User"}
    )
    user.last_chat = message
    user.save()

    # serialization
    serializer = UserSerializer(user)

    if "help" in message.lower():
        return JsonResponse({"reply": "Uh oh. How can I help?", "user": serializer.data, "message": "What can I do?", })

    if message.lower() == 'hey':
        print("What is up?")
        return JsonResponse({"reply": "What's up?"})

    # AI Response
    # Get from openai.com
    try:
        # client = OpenAI(openai_api_key)
        client = OpenAI(
            api_key=config.openai_api_key)
        if city is not None:
            prompt = f"Act as a friendly companion for an elderly person who lives in '{city}'. They said: '{message}'. Respond with dark humor."
            print(prompt)
        else:
            prompt = f"Act as a therapist for an elderly person. They said: '{message}'. Respond warmly and naturally."
            print(prompt)
        #
        # This is the respone back from the AI
        #
        ai_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        ).choices[0].message.content

    except APIConnectionError as e:
        print("Connection error:", e)
        return JsonResponse({"reply": "Sorry, I had trouble connecting!"}, status=503)

    except RateLimitError as e:
        print("Rate limit reached:", e)
        return JsonResponse({"reply": "Too many chats right now—try again soon!"}, status=429)

    except OpenAIError as e:
        print("General OpenAI error:", e)
        return JsonResponse({"reply": "Something’s off with the AI!"}, status=500)

    except Exception as e:
        print("Unexpected error:", e)
        return JsonResponse({"reply": "Oops! Something unexpected happened."}, status=500)

    return JsonResponse({
        "reply": ai_response,
        "user": serializer.data,
        "message": message,
    })


@csrf_exempt
def talk(request):
    '''
    If you're building a simple web-based chat interface, "talk" is your guy.
    '''
    if request.method == "POST":
        message = request.POST.get("message", "").strip()
        lat = request.POST.get("my_lat").strip()
        lon = request.POST.get("my_lon").strip()
        user, _ = User.objects.get_or_create(
            user_name="BigMike", defaults={"first_name": "Test", "last_name": "User"}
        )
        # weather support
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
