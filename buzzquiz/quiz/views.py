from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404
from datetime import datetime
from .models import Answers, Options, Questions, Quiz, QuizEnroll, Users
from .forms import (
    RegQuizenrolls,
    RegistrationFormInstructor,
    UserLoginForm,
    RegistrationFormStudent,
)
from django.contrib.auth.decorators import user_passes_test


def home(request):
    return redirect("/login")


@login_required()
def user_home(request):
    if request.user.is_instructor:
        return redirect("/instructor")
    now = datetime.now()
    now_time = datetime.time(now)
    quizs = list(
        map(lambda x: x.quiz_id.id, QuizEnroll.objects.filter(student_id=request.user))
    )
    queryset = QuizEnroll.objects.filter(
        quiz_id__is_active=True, student_id=request.user
    )
    contex = {
        "completed": {
            "completedCount": queryset.filter(quiz_id__end_date__lt=now).count(),
        },
        "running": {
            "runningCount": queryset.filter(
                quiz_id__end_date__gte=now, quiz_id__start_date__lte=now
            ).count(),
        },
        "upcoming": {
            "upcomingCount": queryset.filter(quiz_id__start_date__gt=now).count(),
        },
    }
    filter = request.GET.get("filter", None)
    if filter is None:
        filter = "running"
    if filter == "running":
        contex["running"]["filter"] = True
        contex["selected"] = queryset.filter(
            quiz_id__end_date__gte=now, quiz_id__start_date__lte=now
        ).order_by("quiz_id__start_date")
    if filter == "upcoming":
        contex["upcoming"]["filter"] = True
        contex["selected"] = queryset.filter(quiz_id__start_date__gt=now).order_by(
            "quiz_id__start_date"
        )
    if filter == "completed":
        contex["completed"]["filter"] = True
        contex["selected"] = queryset.filter(quiz_id__end_date__lt=now).order_by(
            "quiz_id__start_date"
        )
    return render(request, "quiz/home.html", context=contex)


@login_required()
@user_passes_test(lambda user: user.is_instructor, login_url="/user-home")
def instructor_home(request):
    now = datetime.now()
    now_time = datetime.time(now)
    queryset = Quiz.objects.filter(createdBy=request.user, is_active=True)
    contex = {
        "completed": {
            "completedCount": queryset.filter(end_date__lt=now).count(),
        },
        "running": {
            "runningCount": queryset.filter(
                end_date__gte=now, start_date__lte=now
            ).count(),
        },
        "upcoming": {
            "upcomingCount": queryset.filter(start_date__gt=now).count(),
        },
    }
    filter = request.GET.get("filter", None)
    if filter is None:
        filter = "running"
    if filter == "running":
        contex["running"]["filter"] = True
        contex["selected"] = queryset.filter(
            end_date__gte=now, start_date__lte=now
        ).order_by("start_date")
    if filter == "upcoming":
        contex["upcoming"]["filter"] = True
        contex["selected"] = queryset.filter(start_date__gt=now).order_by("start_date")
    if filter == "completed":
        contex["completed"]["filter"] = True
        contex["selected"] = queryset.filter(end_date__lt=now).order_by("start_date")

    return render(request, "quiz/instructor_home.html", context=contex)


def is_auth(user):
    return not user.is_authenticated


@user_passes_test(is_auth, login_url="/user-home")
def login_view(request):
    title = "Login"
    form = UserLoginForm(request.POST or None)
    if form.is_valid():
        email = form.cleaned_data.get("email")
        password = form.cleaned_data.get("password")
        user = authenticate(email=email, password=password)
        flag = False
        if user.last_login is None:
            flag = True
        login(request, user)
        if flag:
            return redirect("/password")
        if request.GET.get("next", None):
            return redirect(request.GET["next"])
        return redirect("/user-home")
    return render(request, "quiz/login.html", {"form": form, "title": title})


def register_student(request):
    title = "Create account"
    if request.method == "POST":
        form = RegistrationFormStudent(request.POST)
        if form.is_valid():
            form.save()
            return redirect("/login")
    else:
        form = RegistrationFormStudent()

    context = {"form": form, "title": title}
    return render(request, "quiz/registration.html", context=context)


def register_instructor(request):
    title = "Create account - Instructor"
    if request.method == "POST":
        form = RegistrationFormInstructor(request.POST)
        if form.is_valid():
            form.save()
            return redirect("/login")
    else:
        form = RegistrationFormInstructor()
    context = {"form": form, "title": title}
    return render(request, "quiz/registration.html", context=context)


def logout_view(request):
    logout(request)
    return redirect("/")


@login_required()
@user_passes_test(lambda user: not user.is_instructor, login_url="/user-home")
def RegQuizenroll(request):
    title = "Enroll Quiz"
    if request.method == "POST":
        form = RegQuizenrolls(request.user, request.POST)
        if form.is_valid():
            QuizEnroll.objects.get_or_create(
                quiz_id=Quiz(id=request.POST["quiz_id"]), student_id=request.user
            )
            return redirect("/")
    else:
        form = RegQuizenrolls(request.user)
    context = {"form": form, "title": title}
    return render(request, "quiz/enroll.html", context=context)


@login_required()
@user_passes_test(lambda user: not user.is_instructor, login_url="/user-home")
def RegQuizenrollURL(request, quiz):
    if request.user.is_instructor == True:
        return redirect("/")
    QuizEnroll.objects.get_or_create(quiz_id=Quiz(id=quiz), student_id=request.user)
    return redirect("/")


def calculate_mark(user: Users, quiz: Quiz):
    mark = 0
    for answer in Answers.objects.filter(user=user, question__quiz=quiz).exclude(
        option=None
    ):
        if answer.question.type == "Single Correct":
            if answer.option.is_correct == True:
                mark += answer.question.mark
            else:
                if answer.question.negative_mark != None:
                    mark -= answer.question.negative_mark
        if answer.question.type == "Multiple Correct":
            total_options = Options.objects.filter(
                question=answer.question, is_correct=True
            ).count()
            if answer.option.is_correct == True:
                mark += answer.question.mark / total_options
    QuizEnroll.objects.filter(student_id=user, quiz_id=quiz).update(mark=mark)


@login_required()
@user_passes_test(lambda user: not user.is_instructor, login_url="/user-home")
def quiz(request, quiz):
    if request.method == "POST":
        question = Questions.objects.get(id=request.POST.get("questionid", None))
        if question.type == "Single Correct":
            keys = [request.POST.get("option", None)]
        else:
            keys = list(request.POST.keys())[2:]
        flag = 0
        for option in Options.objects.filter(id__in=keys):
            # if len(Answers.objects.filter(question=option.question)) == 0:
            flag = 1
            Answers(question=option.question, option=option, user=request.user).save()
        if flag == 0:
            Answers(question=question, option=None, user=request.user).save()
    selected_quiz = Quiz.objects.get(id=quiz)
    answered = [
        x.question.id
        for x in Answers.objects.filter(question__quiz=selected_quiz, user=request.user)
    ]
    questions = Questions.objects.filter(quiz=selected_quiz, mock=False).exclude(
        id__in=answered
    )
    question_to_attend = questions.order_by("?").first()
    if question_to_attend == None:
        calculate_mark(request.user, selected_quiz)
        QuizEnroll.objects.filter(
            student_id=request.user, quiz_id=selected_quiz
        ).update(attended=True)
        return redirect("/")
    options = Options.objects.filter(question=question_to_attend).order_by("?")
    return render(
        request,
        "quiz/attend_quiz.html",
        context={"question": question_to_attend, "options": options},
    )


@login_required()
@user_passes_test(lambda user: not user.is_instructor, login_url="/user-home")
def mock(request, quiz):
    if request.method == "POST":
        question = Questions.objects.get(id=request.POST.get("questionid", None))
        if question.type == "Single Correct":
            keys = [request.POST.get("option", None)]
        else:
            keys = list(request.POST.keys())[2:]
        flag = 0
        for option in Options.objects.filter(id__in=keys):
            if len(Answers.objects.filter(question=option.question)) == 0:
                flag = 1
                Answers(
                    question=option.question, option=option, user=request.user
                ).save()
        if flag == 0:
            Answers(question=question, option=None, user=request.user).save()
    selected_quiz = Quiz.objects.get(id=quiz)
    answered = [
        x.question.id for x in Answers.objects.filter(question__quiz=selected_quiz)
    ]
    questions = Questions.objects.filter(quiz=selected_quiz, mock=True).exclude(
        id__in=answered
    )
    question_to_attend = questions.order_by("?").first()
    if question_to_attend == None:
        Answers.objects.filter(question__id__in=answered, user=request.user).delete()
        return redirect("/")
    options = Options.objects.filter(question=question_to_attend).order_by("?")
    return render(
        request,
        "quiz/attend_quiz.html",
        context={"question": question_to_attend, "options": options},
    )


@login_required()
def answer_key(request, quiz):
    selected_quiz = Quiz.objects.get(id=quiz)
    questions = Questions.objects.filter(quiz=selected_quiz, mock=False)
    context = {
        "questions": [],
    }
    for question in questions:
        options = Options.objects.filter(question=question)
        context["questions"].append({"question": question, "options": options})
    if request.GET.get("user", None) == None:
        context["userid"] = request.user.email
    else:
        if request.user.is_instructor == True:
            context["userid"] = request.GET.get("user", None)
        else:
            context["userid"] = request.user.email
    return render(request, "quiz/answer_key.html", context=context)


@login_required()
@user_passes_test(lambda user: user.is_instructor, login_url="/user-home")
def analytics(request, quiz):
    selected_quiz = Quiz.objects.get(id=quiz)
    students = QuizEnroll.objects.filter(quiz_id=selected_quiz)
    total_mark = 0
    for Question in Questions.objects.filter(quiz=selected_quiz, mock=False):
        total_mark += Question.mark
    context = {
        "attened": students.filter(attended=True).count(),
        "not_attened": students.filter(attended=False).count(),
        "quiz": selected_quiz,
        "enrollments": students,
        "total_marks": total_mark,
    }
    return render(request, "quiz/analytics.html", context=context)


from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm


def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Important!
            messages.success(request, "Your password was successfully updated!")
            return redirect("/login")
        else:
            messages.error(request, "Please correct the error below.")
    else:
        form = PasswordChangeForm(request.user)
    return render(request, "quiz/change_password.html", {"form": form,"title":"Change Password"})
