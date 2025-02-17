from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import CustomUserCreationForm
from .models import Profile


def register(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Создаем профиль и связываем его с пользователем
            Profile.objects.create(
                user=user,
                faculty=form.cleaned_data["faculty"],
                role=form.cleaned_data["role"],
                phone=form.cleaned_data["phone"]
            )
            login(request, user)  # Авторизуем пользователя сразу после регистрации
            return redirect("home")  # Замените "home" на нужный маршрут
    else:
        form = CustomUserCreationForm()
    return render(request, "registration/register.html", {"form": form})
