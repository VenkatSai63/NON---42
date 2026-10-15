from django.urls import path

from . import views

urlpatterns = [path('', views.index, name="home"),
               path("index.html", views.index, name="index"),
	       path('Login.html', views.Login, name="Login"), 
	       path('Register.html', views.Register, name="Register"),
	       path('Signup', views.Signup, name="Signup"),
	       path('UserLogin', views.UserLogin, name="UserLogin"),
	       path('ViewVoters.html', views.ViewVoters, name="ViewVoters"),
	       path('ViewVotersAction', views.ViewVotersAction, name="ViewVotersAction"),
	       path('AddNewVoter.html', views.AddNewVoter, name="AddNewVoter"),
	       path('AddNewVoterAction', views.AddNewVoterAction, name="AddNewVoterAction"),
	       path('RemoveDuplicate', views.RemoveDuplicate, name="RemoveDuplicate"),
	       path('Download', views.Download, name="Download"),
]