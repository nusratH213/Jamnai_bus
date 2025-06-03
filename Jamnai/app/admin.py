from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django import forms
from .models import User  # your custom user model

# 1. Form to create a new user in admin
class UserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ('id', 'role')  # add fields you want

    def clean_password2(self):
        pwd1 = self.cleaned_data.get("password1")
        pwd2 = self.cleaned_data.get("password2")
        if pwd1 and pwd2 and pwd1 != pwd2:
            raise forms.ValidationError("Passwords don't match")
        return pwd2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user

# 2. Form to update user info in admin
class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = ('id', 'password', 'role', 'is_active', 'is_staff')

    def clean_password(self):
        return self.initial["password"]

# 3. Custom UserAdmin class
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = ('id', 'role', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')

    fieldsets = (
        (None, {'fields': ('id', 'password')}),
        ('Permissions', {'fields': ('role', 'is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('id', 'role', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )
    search_fields = ('id',)
    ordering = ('id',)
    filter_horizontal = ('groups', 'user_permissions',)

# 4. Register your User model with this UserAdmin
admin.site.register(User, UserAdmin)
