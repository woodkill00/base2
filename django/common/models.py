import uuid
import zoneinfo

from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from phonenumber_field.modelfields import PhoneNumberField

User = get_user_model()

# Notes / optional imports kept for future reference:
# from django.contrib.gis.db import models
# from enum import unique
# from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
# from djmoney.models.fields import MoneyField
# from django.db.models.fields import CharField
# from django.utils import timezone
# from django_countries import countries
# from django_countries import CountryTuple, countries
# from model_utils import Choices


class ID(models.Model):

    pkid = models.AutoField(
        verbose_name=_("Primary Key ID"),
        primary_key=True,
        editable=False,
        help_text=_("Internal primary key id"),
    )
    id = models.UUIDField(
        verbose_name=_("ID"),
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text=_("Internal ID"),
    )

    class Meta:
        verbose_name = _("ID")
        verbose_name_plural = _("IDs")
        abstract = True
        # get_latest_by = ['-priority', 'order_date']
        # ordering = ['-order_date']

    def __str__(self):
        return self.pkid


class Created(models.Model):
    created = models.DateTimeField(
        auto_now_add=True,
        # default=timezone.now,
        verbose_name=_("Created On"),
        help_text=_("Date/Time created in database"),
    )

    class Meta:
        verbose_name = _("Created")
        verbose_name_plural = _("Created On")
        abstract = True

    def __str__(self):
        return self.created


class Updated(models.Model):
    updated = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Last Updated On"),
        help_text=_("Date/Time last updated in database"),
    )

    class Meta:
        verbose_name = _("Updated")
        verbose_name_plural = _("Updated On")
        abstract = True

    def __str__(self):
        return self.updated


class TimestampedModel(models.Model):
    created = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created On"),
        help_text=_("Date/Time created in database"),
    )
    updated = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Last Updated On"),
        help_text=_("Date/Time last updated in database"),
    )

    class Meta:
        verbose_name = _("Timestamped Model")
        verbose_name_plural = _("Timestamped Models")
        abstract = True


class UUIDMixin(models.Model):
    uuid = models.UUIDField(
        verbose_name=_("UUID"),
        default=uuid.uuid4,
        editable=False,
        unique=True,
        help_text=_("Non-primary UUID identifier"),
    )

    class Meta:
        verbose_name = _("UUID Mixin")
        verbose_name_plural = _("UUID Mixins")
        abstract = True


# class Name(models.Model):
#     name = models.CharField(
#         verbose_name=_("Name"),
#         max_length=150,
#         blank=True,
#         unique=True,
#         help_text=_("Name"),
#     )

#     class Meta:
#         verbose_name = _("Name")
#         verbose_name_plural = _("Names")
#         abstract = True
#         # get_latest_by = ['-priority', 'order_date']
#         # ordering = ['-order_date']

#     def __str__(self):
#         return self.name


class Timezone(models.Model):

    TIMEZONE_CHOICES = (
        (x, x) for x in sorted(zoneinfo.available_timezones(), key=str.lower)
    )
    timezone = models.CharField(
        verbose_name=_("IANA Time Zone"),
        choices=TIMEZONE_CHOICES,
        max_length=255,
        blank=True,
        default=_("America/New_York"),
        help_text=_("Timezone"),
    )
    # utc_offset = models.FloatField(
    #     verbose_name=_("UTC Offset"),
    #     choices=COMPANY_UTC_OFFSET_CHOICES,
    #     default=(0),
    #     # blank=True,
    #     validators=[
    #         MinValueValidator(-12),
    #         MaxValueValidator(14)
    #     ],
    #     help_text=_("UTC offset Time min=-12 / max=14"),
    # )

    class Meta:
        verbose_name = _("Timezone")
        verbose_name_plural = _("Timezones")
        abstract = True

    def __str__(self):
        return self.timezone


class Address(models.Model):
    # pkid = models.AutoField(
    #     verbose_name=_("Primary Key ID"),
    #     primary_key=True,
    #     editable=False,
    #     help_text=_("Internal primary key id for base address"),
    # )
    # id = models.UUIDField(
    #     verbose_name=_("ID"),
    #     default=uuid.uuid4,
    #     editable=False,
    #     unique=True,
    #     help_text=_("Internal ID for address"),
    # )
    # name = models.CharField(
    #     verbose_name=_("Name"),
    #     max_length=150,
    #     blank=True,
    #     unique=True,
    #     help_text=_("Name"),
    # )
    line1 = models.CharField(
        verbose_name=_("Address Line 1"),
        max_length=255,
        # blank=True,
        # default='',
        help_text=_("Street Line 1"),
    )
    line2 = models.CharField(
        verbose_name=_("Address Line 2"),
        max_length=255,
        blank=True,
        default="",
        help_text=_("Address Line 2"),
    )
    city = models.CharField(
        verbose_name=_("City"),
        max_length=150,
        # blank=True,
        # default='',
        help_text=_("City Name"),
    )
    state = models.CharField(
        verbose_name=_("State"),
        max_length=150,
        blank=True,
        null=True,
        # default='',
        help_text=_("State Name"),
    )
    state_code = models.CharField(
        verbose_name=_("State Code"),
        max_length=5,
        blank=True,
        null=True,
        # default='',
        help_text=_("State Code"),
    )
    postal_code = models.PositiveIntegerField(
        verbose_name=_("Postal Zip Code"),
        blank=True,
        null=True,
        # default='',
        validators=[MinValueValidator(0), MaxValueValidator(999999999)],
        help_text=_("Postal Zip Code"),
    )
    country = CountryField(
        blank_label=_("Select Country"),
        verbose_name=_("Country"),
        max_length=150,
        # default='',
        help_text=_("Country Name"),
    )
    latitude = models.DecimalField(
        verbose_name=_("Latitude"),
        blank=True,
        null=True,
        default="",
        max_digits=18,
        decimal_places=15,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text=_("Latitude"),
    )
    longitude = models.DecimalField(
        verbose_name=_("Longitude"),
        blank=True,
        null=True,
        default="",
        max_digits=18,
        decimal_places=15,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
        help_text=_("Longitude"),
    )
    # location = models.PointField(
    #     verbose_name=_("Lat and Lon"),
    #     help_text=_("Lat/Lon"),
    # )
    street_number = models.PositiveIntegerField(
        verbose_name=_("Street Number"),
        blank=True,
        null=True,
        # default="",
        validators=[MinValueValidator(0), MaxValueValidator(99999)],
        help_text=_("Street Number"),
    )
    street_number_before_name = models.BooleanField(
        verbose_name=_("Street Number Before Name"),
        default=False,
        help_text=_("Street Number > Street Name"),
    )
    street_name = models.CharField(
        verbose_name=_("Street Name"),
        max_length=150,
        blank=True,
        # default="",
        help_text=_("Street Name"),
    )
    sub_premise = models.PositiveIntegerField(
        verbose_name=_("Suite Number"),
        blank=True,
        null=True,
        # default="",
        validators=[MinValueValidator(0), MaxValueValidator(9999)],
        help_text=_("Suite Number"),
    )
    sub_premise_name = models.CharField(
        verbose_name=_("Sub Premise Name"),
        max_length=150,
        blank=True,
        # default="",
        help_text=_("Sub Premise Name"),
    )

    class Meta:
        verbose_name = _("Address")
        verbose_name_plural = _("Addresses")
        abstract = True

    # def __str__(self):
    #     return self.name

    # def __str__(self):
    #     return self.name

    # def get_geo_location(self):
    #     return f"lat: {self.latitude}, lat: {self.longitude}"

    # def get_country_name(self):
    #     return self.country.name

    # def get_country_code(self):
    #     return self.country.code

    # def get_country_alpha3(self):
    #     return self.country.alpha3

    # def get_country_numeric(self):
    #     return self.country.numeric

    # def get_country_numeric_padded(self):
    #     return self.country.numeric_padded

    # def get_country_ioc_code(self):
    #     return self.country.ioc_code


class Category(models.Model):
    name = models.CharField(
        # default=_("UNKNOWN"),
        verbose_name=_("Category Name"),
        unique=True,
        blank=True,
        default="",
        max_length=255,
        help_text=_("Category name"),
    )

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        abstract = True

    def __str__(self):
        return self.name


class Domain(models.Model):
    name = models.CharField(
        verbose_name=_("Domain Name"),
        max_length=255,
        help_text=_("Domain Name"),
    )

    class Meta:
        verbose_name = _("Domain Name")
        verbose_name_plural = _("Domain Names")
        abstract = True

    def __str__(self):
        return self.name


class Email(models.Model):

    email = models.EmailField(
        verbose_name=_("Email Address"),
        max_length=255,
        unique=True,
        help_text=_("Email Address"),
    )

    class Meta:
        verbose_name = _("Email Address")
        verbose_name_plural = _("Email Addresses")
        abstract = True

    def __str__(self):
        return self.email


class IpAddress(models.Model):
    address = models.GenericIPAddressField(
        verbose_name=_("Ip Address"),
        max_length=255,
        blank=True,
        null=True,
        default="",
        help_text=_("Ip Address"),
    )

    class Meta:
        verbose_name = _("Ip Address")
        verbose_name_plural = _("Ip Addresses")
        abstract = True

    def __str__(self):
        return self.address


class Phonenumber(models.Model):
    phonenumber = PhoneNumberField(
        verbose_name=_("Phonenumber"),
        help_text=_("Phonenumber"),
    )

    class Meta:
        verbose_name = _("Phonenumber")
        verbose_name_plural = _("Phonenumbers")
        abstract = True

    def __str__(self):
        return self.phonenumber


class Staff(models.Model):
    member = models.ForeignKey(
        User,
        verbose_name=_("Staff member"),
        blank=True,
        on_delete=models.CASCADE,
        help_text=_("Staff member"),
    )

    class Meta:
        verbose_name = _("Staff")
        verbose_name_plural = _("Staffs")
        abstract = True

    def __str__(self):
        return f"{self.member}"


class Tag(models.Model):
    name = models.CharField(
        # default=_("UNKNOWN"),
        verbose_name=_("Tag Name"),
        unique=True,
        max_length=255,
        help_text=_("Tag name"),
    )

    class Meta:
        verbose_name = _("Tag")
        verbose_name_plural = _("Tags")
        abstract = True

    def __str__(self):
        return self.name


class Url(models.Model):
    address = models.URLField(
        verbose_name=_("Url Address"),
        unique=True,
        max_length=255,
        help_text=_("Url Address"),
    )

    class Meta:
        verbose_name = _("Url Address")
        verbose_name_plural = _("Url Addresses")
        abstract = True

    def __str__(self):
        return self.address