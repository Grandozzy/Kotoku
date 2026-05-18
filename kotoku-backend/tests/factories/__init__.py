"""
Shared test factories for Kotoku.

Usage:
    from tests.factories import AccountFactory, AgreementFactory, SealedAgreementFactory

    acct = AccountFactory()
    agr = SealedAgreementFactory(created_by=acct)
    party = agr.parties.first()
"""
import factory
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import Account, User
from apps.agreements.domain.enums import AgreementStatus
from apps.agreements.models import Agreement
from apps.evidence.models import EvidenceItem
from apps.parties.models import Party


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    phone = factory.Sequence(lambda n: f"+2339{n:08d}")


class AccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Account

    user = factory.SubFactory(UserFactory)
    phone = factory.LazyAttribute(lambda o: o.user.phone)
    email = factory.Sequence(lambda n: f"user{n}@kotoku-test.com")


class AgreementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Agreement

    title = factory.Sequence(lambda n: f"Test Agreement {n}")
    scenario_template = "used_vehicle_sale"
    status = AgreementStatus.DRAFT
    created_by = factory.SubFactory(AccountFactory)


class PartyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Party

    agreement = factory.SubFactory(AgreementFactory)
    display_name = factory.Sequence(lambda n: f"Party {n}")
    phone = factory.Sequence(lambda n: f"+2337{n:08d}")
    role = Party.Role.SELLER


class SealedAgreementFactory(factory.django.DjangoModelFactory):
    """Creates a sealed agreement with two parties and required evidence."""

    class Meta:
        model = Agreement
        exclude = ["seller_phone", "buyer_phone"]

    title = factory.Sequence(lambda n: f"Sealed Agreement {n}")
    scenario_template = "used_vehicle_sale"
    status = AgreementStatus.SEALED
    created_by = factory.SubFactory(AccountFactory)
    sealed_at = factory.LazyFunction(timezone.now)
    seal_hash = factory.Sequence(lambda n: f"hash{n:032x}")

    seller_phone = factory.LazyAttribute(lambda o: o.created_by.phone)
    buyer_phone = factory.Sequence(lambda n: f"+2336{n:08d}")

    @factory.post_generation
    def parties(self, create, extracted, **kwargs):
        if not create:
            return
        PartyFactory(
            agreement=self,
            phone=self.seller_phone,
            role=Party.Role.SELLER,
            display_name="Seller",
        )
        PartyFactory(
            agreement=self,
            phone=self.buyer_phone,
            role=Party.Role.BUYER,
            display_name="Buyer",
        )

    @factory.post_generation
    def evidence(self, create, extracted, **kwargs):
        if not create:
            return
        EvidenceItem.objects.create(
            agreement=self,
            file_type=EvidenceItem.FileType.PHOTO,
            evidence_type="vehicle_photo_front",
            mime_type="image/jpeg",
            upload_status=EvidenceItem.UploadStatus.CONFIRMED,
            storage_url=f"https://storage.kotoku/fake/{self.pk}.jpg",
        )


def make_authenticated_client(account: Account) -> APIClient:
    """Return an APIClient authenticated as the given account."""
    token = AccessToken.for_user(account.user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return client
