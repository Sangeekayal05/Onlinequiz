from optparse import Option
from django.contrib import admin
from .models import Answers, Options, Questions, Quiz, Users, QuizEnroll
from django.utils.translation import ugettext_lazy as _
from nested_inline.admin import (
    NestedModelAdmin,
    NestedStackedInline,
    NestedTabularInline,
)
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.shortcuts import redirect
from django.utils.crypto import get_random_string

class UsersAdmin(BaseUserAdmin):
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('institute',)}),
        (_('Permissions'), {'fields': ('is_staff', 'is_superuser',
                                        'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'institute', 'password1', 'password2'),
        }),
    )
    list_display = ("email", "first_name", "last_name", "institute", "is_instructor",)
    list_filter = ("is_instructor", "is_staff",)
    search_fields = ("email", "first_name", "last_name", "institute",)
    ordering = ('email',)
    
class OptionsInline(NestedStackedInline):
    model = Options
    extra = 1
    fk_name = "question"


class QuestionsInline(NestedStackedInline):
    model = Questions
    extra = 1
    fk_name = "quiz"
    inlines = [OptionsInline]


class QuizAdmin(NestedModelAdmin):
    list_filter = ("is_active",)
    search_fields = ("name",)
    readonly_fields = ("createdBy",'id')
    exclude = []
    model = Quiz
    inlines = [QuestionsInline]

    def get_exclude(self, request, obj):
        if request.user.is_superuser:
            return super().get_exclude(request, obj)
        return list(super().get_exclude(request, obj)).extend(['created_at'])

    def save_model(self, request, obj, form, change):
        if request.user.groups.filter(name='instructors').exists():
            obj.createdBy = request.user
        if not obj.id:
            id = get_random_string(6)
            while len(self.model.objects.filter(id=id)) != 0 :
                id = get_random_string(6)
            obj.id = id
        super().save_model(request, obj, form, change)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(createdBy=request.user)

    def response_add(self, request, obj, post_url_continue=None):
        return redirect('/user-home')
    def response_change(self, request, obj):
        return redirect('/user-home')
    def response_delete(self, request, obj_display, obj_id):
        return redirect('/user-home')

admin.site.register(Quiz, QuizAdmin)
admin.site.register(Users, UsersAdmin)
admin.site.register(QuizEnroll)
admin.site.register(Answers)
