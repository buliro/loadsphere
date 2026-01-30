from django.contrib import admin
from django.urls import path, include, re_path
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static

from planner.views import auth as auth_views
from planner.views import eld as eld_views
from planner.views import csrf as csrf_views
from planner.views import openroute as openroute_views
from planner.views import reports as report_views

from graphene_django.views import GraphQLView
from django.views.decorators.csrf import csrf_exempt

graphql_view = csrf_exempt(GraphQLView.as_view(graphiql=True))

default_urlpatterns = [
    path('admin/', admin.site.urls),
    path('graphql/', graphql_view, name='graphql'),
    path('api/graphql/', graphql_view, name='api-graphql'),
    path('api/csrf/', csrf_views.csrf_token_view, name='csrf-token'),
    path('api/auth/register/', auth_views.register_view, name='register'),
    path('api/auth/login/', auth_views.login_view, name='login'),
    path('api/auth/logout/', auth_views.logout_view, name='logout'),
    path('api/auth/session/', auth_views.session_view, name='session'),
    path('api/eld/trips/', eld_views.eld_trips_view, name='eld-trips'),
    path('api/eld/trips/<int:trip_id>/', eld_views.eld_trip_detail_view, name='eld-trip-detail'),
    path('api/openroute/search/', openroute_views.search_locations_view, name='openroute-search'),
    path('api/openroute/route/', openroute_views.route_distance_view, name='openroute-route'),
    path('api/routes/<int:trip_id>/report.pdf', report_views.trip_pdf_report_view, name='route-report-pdf'),
]

# Base URL patterns
urlpatterns = list(default_urlpatterns)

# Serve static files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Serve React app for all other routes (must be last)
urlpatterns += [
    re_path(r'^.*$', TemplateView.as_view(template_name='index.html')),
]
