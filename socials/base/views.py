from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout, update_session_auth_hash
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password
from django.contrib.auth.models import User
from django.views.generic import DetailView, CreateView, UpdateView, DeleteView, ListView
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy, reverse
from itertools import chain
import random

from .models import *
from .forms import *

# Home feed view
@login_required(login_url='login')
def home(request):
    user_object = User.objects.get(username=request.user.username)
    user_profile, created = Profile.objects.get_or_create(user=user_object)
    all_users = User.objects.all()
    all_posts = Post.objects.all()
    all_profile = Profile.objects.all()
    count_posts = len(all_posts)

    suggestion_users = [user for user in all_profile if user != user_profile]
    random.shuffle(suggestion_users)

    context = {
        'user_object': user_object,
        'user_profile': user_profile,
        'all_users': all_users,
        'all_posts': all_posts,
        'all_profile': all_profile,
        'count_posts': count_posts,
        'suggestion_users': suggestion_users,
    }
    return render(request, "base/home.html", context)

# Show other user's profile
class ShowProfilePageView(DetailView):
    model = Profile
    template_name = 'base/Otherprofile.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        page_user = get_object_or_404(Profile, id=self.kwargs['pk'])
        logged_in_user_posts = Post.objects.filter(author=page_user)

        button_text = 'UnFollow' if FollowersCount.objects.filter(user=page_user).exists() else 'Follow'

        context.update({
            "page_user": page_user,
            "logged_in_user_posts": logged_in_user_posts,
            "num_posts": len(logged_in_user_posts),
            "button_text": button_text,
            "user_followers": FollowersCount.objects.filter(user=page_user).count(),
            "user_following": FollowersCount.objects.filter(follower=page_user).count(),
        })
        return context

# Login view
def login(request):
    if request.user.is_authenticated:
        return redirect('/')
    if request.method == "POST":
        username = request.POST.get('username')
        password = request.POST["password"]
        user = authenticate(request, username=username, password=password)
        if user:
            auth_login(request, user)
            messages.info(request, 'You have successfully logged in.')
            return redirect('/')
        else:
            messages.info(request, 'Invalid username or password.')
    return render(request, "base/login.html")

# Signup view
def signup(request):
    if request.user.is_authenticated:
        return redirect('/')
    if request.method == 'POST':
        email = request.POST['email'].strip()
        password = request.POST['password']
        username = request.POST['username']

        if not email or not password or not username:
            messages.error(request, "Please fill all the fields.")
        elif User.objects.filter(username=username).exists():
            messages.info(request, 'Username already exists.')
        elif User.objects.filter(email=email).exists():
            messages.info(request, 'Email already exists.')
        else:
            user = User.objects.create(email=email, username=username, password=make_password(password))
            auth_login(request, user)
            messages.info(request, 'You have successfully signed up.')
            return redirect('/create_profile_page')
    return render(request, "base/signup.html")

# Logout view
def logout(request):
    auth_logout(request)
    return redirect('/')

# Friends view
class FriendView(ListView):
    model = Profile
    template_name = 'base/friends.html'
    ordering = ['-id']

# New post view
@login_required(login_url='login')
def new_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect('/')
        else:
            print(form.errors)
    else:
        form = PostForm()
    return render(request, 'base/add_post.html', {'form': form})


# Create profile page
class CreateProfilePageView(CreateView):
    model = Profile
    form_class = ProfilePageForm
    template_name = "base/create_user_profile.html"

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

# Edit profile page
class EditProfilePageView(UpdateView):
    model = Profile
    form_class = EditProfileNewForm
    template_name = 'base/edit_profile_page.html'
    success_url = reverse_lazy('home')

# Password change view
class PasswordsChangeView(PasswordChangeView):
    form_class = PasswordChangingForm
    success_url = reverse_lazy('password_success')

def password_success(request):
    return render(request, 'base/password_success.html')

# Add comment view
class AddCommentView(CreateView):
    model = Comment
    form_class = CommentForm
    template_name = 'base/add_comment.html'

    def form_valid(self, form):
        form.instance.post_id = self.kwargs['pk']
        return super().form_valid(form)

# Like post view
@login_required(login_url='login')
def like_post(request):
    username = request.user.username
    post_id = request.GET.get('post_id')
    post = Post.objects.get(id=post_id)
    like_filter = LikePost.objects.filter(post_id=post_id, username=username).first()

    if not like_filter:
        LikePost.objects.create(post_id=post_id, username=username)
        post.no_of_likes += 1
    else:
        like_filter.delete()
        post.no_of_likes -= 1
    post.save()
    return redirect('/')

# Delete post view
class DeletePostView(DeleteView):
    model = Post
    template_name = 'base/delete_post.html'
    success_url = reverse_lazy('home')

# Search view
@login_required(login_url='login')
def search(request):
    user_object = User.objects.get(username=request.user.username)
    user_profile = Profile.objects.get(user=user_object)
    username_profile_list = []

    if request.method == 'POST':
        username = request.POST['username']
        username_objects = Profile.objects.filter(username__icontains=username)
        username_profile_list = list(username_objects)

    return render(request, 'base/search.html', {
        'user_profile': user_profile,
        'username_profile_list': username_profile_list,
    })

# Update post view
class UpdatePostView(UpdateView):
    model = Post
    form_class = EditForm
    template_name = 'base/update_post.html'

# Follow / unfollow view
@login_required(login_url='login')
def follow(request):
    if request.method == 'POST':
        follower = request.POST['follower']
        user = request.POST['user']

        existing_follow = FollowersCount.objects.filter(follower=follower, user=user).first()
        if existing_follow:
            existing_follow.delete()
        else:
            FollowersCount.objects.create(follower=follower, user=user)
        return redirect('/')
    return redirect('/')
