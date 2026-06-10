import re

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .india_locations import INDIAN_STATES, cities_for_state, is_valid_city, normalize_state
from .models import Address

User = get_user_model()

STATE_CHOICES = [("", "Select state")] + [(state, state) for state in INDIAN_STATES]


class MobileLoginForm(forms.Form):
    mobile_number = forms.CharField(
        label="Mobile Number",
        widget=forms.TextInput(attrs={
            "placeholder": "10-digit mobile number",
            "class": "form-control form-control-lg",
            "inputmode": "numeric",
            "autocomplete": "tel",
            "maxlength": "10",
        }),
    )

    def clean_mobile_number(self):
        from .twilio_verify import normalize_indian_mobile, TwilioVerifyError
        mobile = self.cleaned_data["mobile_number"].strip()
        try:
            return normalize_indian_mobile(mobile)
        except TwilioVerifyError as exc:
            raise forms.ValidationError(str(exc)) from exc


class OtpVerifyForm(forms.Form):
    otp_code = forms.CharField(
        label="Verification code",
        max_length=8,
        widget=forms.TextInput(attrs={
            "placeholder": "Enter 6-digit OTP",
            "class": "form-control form-control-lg text-center otp-input",
            "inputmode": "numeric",
            "autocomplete": "one-time-code",
            "maxlength": "8",
        }),
    )

    def clean_otp_code(self):
        code = self.cleaned_data["otp_code"].strip()
        if not code.isdigit() or len(code) < 4:
            raise forms.ValidationError("Enter the verification code sent to your phone.")
        return code


class AddressForm(forms.ModelForm):
    state = forms.ChoiceField(
        choices=STATE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select", "id": "id_state"}),
    )
    city = forms.ChoiceField(
        choices=[("", "Select state first")],
        widget=forms.Select(attrs={"class": "form-select", "id": "id_city"}),
    )

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
            "mobile_number": forms.TextInput(attrs={"class": "form-control", "placeholder": "10-digit mobile number"}),
            "address_line": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "House / flat / street / area",
                "id": "id_address_line",
            }),
            "landmark": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nearby landmark", "id": "id_landmark"}),
            "pincode": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "6-digit pincode",
                "id": "id_pincode",
                "maxlength": "6",
                "pattern": "[0-9]{6}",
            }),
            "latitude": forms.HiddenInput(attrs={"id": "id_latitude"}),
            "longitude": forms.HiddenInput(attrs={"id": "id_longitude"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        selected_state = ""
        selected_city = ""
        if self.instance and self.instance.pk:
            selected_state = normalize_state(self.instance.state)
            selected_city = self.instance.city
        elif self.is_bound:
            selected_state = normalize_state(self.data.get("state", ""))
            selected_city = self.data.get("city", "")

        if selected_state:
            city_choices = [("", "Select city")] + [
                (city, city) for city in cities_for_state(selected_state)
            ]
            self.fields["city"].choices = city_choices
            if selected_city and selected_city not in cities_for_state(selected_state):
                self.fields["city"].choices.append((selected_city, selected_city))
        else:
            self.fields["city"].choices = [("", "Select state first")]

        if selected_state:
            self.initial["state"] = selected_state
        if selected_city:
            self.initial["city"] = selected_city

    def clean_mobile_number(self):
        mobile = self.cleaned_data["mobile_number"].strip()
        if not mobile.isdigit() or len(mobile) != 10:
            raise forms.ValidationError("Enter a valid 10-digit mobile number.")
        return mobile

    def clean_pincode(self):
        pincode = self.cleaned_data["pincode"].strip()
        if not re.fullmatch(r"\d{6}", pincode):
            raise forms.ValidationError("Enter a valid 6-digit Indian pincode.")
        return pincode

    def clean_state(self):
        state = normalize_state(self.cleaned_data.get("state", ""))
        if not state or state not in INDIAN_STATES:
            raise forms.ValidationError("Please select a valid Indian state.")
        return state

    def clean(self):
        cleaned_data = super().clean()
        state = cleaned_data.get("state")
        city = cleaned_data.get("city")
        if not state:
            self.add_error("state", "Please select a state first.")
            return cleaned_data
        if not city:
            self.add_error("city", "Please select a city.")
            return cleaned_data
        if not is_valid_city(state, city):
            self.add_error("city", "Please select a valid city for the chosen state.")
        return cleaned_data


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
