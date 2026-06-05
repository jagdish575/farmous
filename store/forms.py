from django import forms
from django.contrib.auth import get_user_model
from .models import Address

User = get_user_model()

class MobileLoginForm(forms.Form):
    mobile_number = forms.CharField(
        label="Mobile Number",
        widget=forms.TextInput(attrs={"placeholder": "Enter mobile number", "class": "form-control"}),
    )

    def clean_mobile_number(self):
        mobile = self.cleaned_data["mobile_number"].strip()
        if not mobile.isdigit() or len(mobile) < 10:
            raise forms.ValidationError("Enter a valid mobile number.")
        return mobile

class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = [
            "full_name",
            "mobile_number",
            "address_line",
            "landmark",
            "city",
            "state",
            "pincode",
            "latitude",
            "longitude",
        ]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Full name"}),
            "mobile_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "Mobile number"}),
            "address_line": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "House number, street, area"}),
            "landmark": forms.TextInput(attrs={"class": "form-control", "placeholder": "Landmark"}),
            "city": forms.TextInput(attrs={"class": "form-control", "placeholder": "City"}),
            "state": forms.TextInput(attrs={"class": "form-control", "placeholder": "State"}),
            "pincode": forms.TextInput(attrs={"class": "form-control", "placeholder": "Pincode"}),
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
        }

    def clean_mobile_number(self):
        mobile = self.cleaned_data["mobile_number"].strip()
        if not mobile.isdigit() or len(mobile) < 10:
            raise forms.ValidationError("Enter a valid mobile number.")
        return mobile

class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["full_name", "mobile_number"]
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "form-control form-control-lg", "placeholder": "Your full name"}),
            "mobile_number": forms.TextInput(attrs={"class": "form-control form-control-lg", "placeholder": "10-digit mobile number"}),
        }

    def clean_mobile_number(self):
        mobile = self.cleaned_data["mobile_number"].strip()
        if not mobile.isdigit() or len(mobile) < 10:
            raise forms.ValidationError("Enter a valid mobile number.")
        return mobile

class NotificationSettingsForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["notify_order_updates", "notify_promotions", "notify_refill_reminders"]
        widgets = {
            "notify_order_updates": forms.CheckboxInput(attrs={"class": "form-check-input", "role": "switch"}),
            "notify_promotions": forms.CheckboxInput(attrs={"class": "form-check-input", "role": "switch"}),
            "notify_refill_reminders": forms.CheckboxInput(attrs={"class": "form-check-input", "role": "switch"}),
        }
