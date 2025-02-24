from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
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
    return render(request, "user/register.html", {"form": form})

def login_view(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            # Аутентификация пользователя
            user = form.get_user()
            login(request, user)

            # Перенаправление на страницу, с которой пользователь пришел
            next_url = request.GET.get('next', '/')
            return redirect(next_url)
    else:
        form = AuthenticationForm()

    return render(request, "user/login.html", {"form": form})



def logout_view(request):
    # Завершаем сеанс пользователя
    logout(request)
    # Перенаправляем на страницу логина после выхода
    return redirect('login')  # или '/user/login/' если хотите явно указывать путь