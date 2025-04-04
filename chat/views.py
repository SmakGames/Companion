from django.shortcuts import render
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view
from .models import User, UserProfile
from .serializers import UserSerializer, UserProfileSerializer, UserProfileCreateSerializer


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


@csrf_exempt
def talk(request):
    if request.method == "POST":
        message = request.POST.get("message", "")
        user, _ = User.objects.get_or_create(
            user_name="TestUser", defaults={"first_name": "Test", "last_name": "User"}
        )
        # weather support
        import requests
        api_key = "91e174a545a3ab9fd6b6a7aa7b8785b1"
        try:
            weather = requests.get(
                f"http://api.openweathermap.org/data/2.5/weather?q=Milwaukee&appid={api_key}&units=imperial"
            ).json()
            temp = weather["main"]["temp"] if weather.get(
                "main") else "unknown"
        except (requests.RequestException, KeyError):
            temp = "unknown"

        response = f"You said: {message}. I remember you, {user.first_name}! It is {temp} out today."
        user.last_chat = message
        user.save()

        return HttpResponse(response)

    return render(request, "chat/talk.html")


@api_view(['POST'])
@csrf_exempt
def talk_api(request):
    message = request.data.get("message", "")
    user, _ = User.objects.get_or_create(
        user_name="TestUser", defaults={"first_name": "Test", "last_name": "User"}
    )
    user.last_chat = message
    user.save()
    import requests
    api_key = "91e174a545a3ab9fd6b6a7aa7b8785b1"
    try:
        weather = requests.get(
            f"http://api.openweathermap.org/data/2.5/weather?q=Milwaukee&appid={api_key}&units=imperial"
        ).json()
        temp = weather["main"]["temp"] if weather.get("main") else "unknown"
    except (requests.RequestException, KeyError):
        temp = "unknown"
    serializer = UserSerializer(user)
    return Response({
        "reply": f"You said: {message}. I remember you, {user.first_name}! It’s {temp}°F out.",
        "user": serializer.data
    })
