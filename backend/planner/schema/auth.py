import graphene
import graphql_jwt
from graphene_django import DjangoObjectType
from graphene_django.types import ErrorType
from graphql_jwt.shortcuts import get_token, create_refresh_token
from graphql_jwt.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.core.exceptions import ValidationError as DjangoValidationError


def validate_email_address(email: str) -> bool:
    """Validate an email address using Django's built-in validator.

    Args:
        email: Email address string provided by the client.

    Returns:
        bool: True if the email is considered valid, otherwise False.
    """

    try:
        validate_email(email)
        return True
    except DjangoValidationError:
        return False


class RegisterInput(graphene.InputObjectType):
    """GraphQL input object describing registration fields for a new user."""

    email = graphene.String(required=True)
    username = graphene.String(required=True)
    password1 = graphene.String(required=True)
    password2 = graphene.String(required=True)
    first_name = graphene.String()
    last_name = graphene.String()


class Register(graphene.Mutation):
    """Mutation handling user registration and JWT issuance."""

    class Arguments:
        input = RegisterInput(required=True)

    success = graphene.Boolean()
    token = graphene.String()
    refresh_token = graphene.String()
    errors = graphene.List(ErrorType)

    @classmethod
    def mutate(cls, root, info, input):
        """Create a new user account and return authentication tokens.

        Args:
            root: GraphQL root object (unused).
            info: GraphQL execution info containing context and request.
            input: RegisterInput payload with user data.

        Returns:
            Register: Mutation payload including success flag, tokens, and errors.
        """

        errors = []
        User = get_user_model()

        # Validate email
        if not validate_email_address(input.email):
            errors.append(ErrorType(field='email', messages=['Enter a valid email address.']))

        # Check if email is already registered
        if User.objects.filter(email=input.email).exists():
            errors.append(ErrorType(field='email', messages=['A user with this email already exists.']))

        # Check if username is taken
        if User.objects.filter(username=input.username).exists():
            errors.append(ErrorType(field='username', messages=['A user with this username already exists.']))

        # Validate password
        if len(input.password1) < 8:
            errors.append(ErrorType(field='password1', messages=['This password is too short. It must contain at least 8 characters.']))

        if input.password1 != input.password2:
            errors.append(ErrorType(field='password2', messages=["The two password fields didn't match."]))

        if errors:
            return Register(success=False, errors=errors, token=None, refresh_token=None)

        try:
            user = User.objects.create_user(
                username=input.username,
                email=input.email,
                password=input.password1,
                first_name=getattr(input, 'first_name', ''),
                last_name=getattr(input, 'last_name', '')
            )

            return Register(
                success=True,
                token=get_token(user),
                refresh_token=create_refresh_token(user),
                errors=[]
            )
        except Exception as e:
            errors.append(ErrorType(field=None, messages=[str(e)]))
            return Register(success=False, errors=errors, token=None, refresh_token=None)


class AuthMutation(graphene.ObjectType):
    """GraphQL mutations related to authentication and token lifecycle."""

    register = Register.Field()
    token_auth = graphql_jwt.ObtainJSONWebToken.Field()
    verify_token = graphql_jwt.Verify.Field()
    refresh_token = graphql_jwt.Refresh.Field()
    revoke_token = graphql_jwt.Revoke.Field()


class UserType(DjangoObjectType):
    """GraphQL type exposing limited user fields for authenticated queries."""

    class Meta:
        model = get_user_model()
        interfaces = (graphene.relay.Node,)
        fields = (
            'id',
            'username',
            'email',
            'first_name',
            'last_name',
            'is_staff',
            'is_active',
        )


class UserQuery(graphene.ObjectType):
    """Query mixin providing the currently authenticated user."""

    me = graphene.Field(UserType)

    @login_required
    def resolve_me(self, info):
        """Return the requesting user when authenticated."""

        return info.context.user


# Update the mutations.py to include auth mutations
from .mutations import Mutation as BaseMutation


class Mutation(BaseMutation, AuthMutation, graphene.ObjectType):
    """Combined GraphQL mutation root including core and auth operations."""

    pass
