from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from .forms import RegisterForm, PostForm, CommentForm
from .models import Post, Comment, Follow
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden


def home(request):
    return render(request, 'main/home.html')


def index(request):
    return render(request, 'main/index.html')


def register_view(request):
    form = RegisterForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        login(request, user)
        return redirect('index')
    return render(request, 'main/register.html', {'form': form})

@login_required
def index_view(request):
    if request.GET.get('all'):
        posts = Post.objects.all().order_by('-created_at')
    else:
        following_ids = Follow.objects.filter(follower=request.user).values_list('following_id', flat=True)
        if following_ids.exists():
            posts = Post.objects.filter(author__id__in=following_ids).order_by('-created_at')
        else:
            posts = Post.objects.all().order_by('-created_at')

    form = PostForm(request.POST or None, request.FILES or None)

    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect('index')

    # 👉 Принудительно обновим связи following
    request.user.refresh_from_db()
    following_users = [f.following for f in Follow.objects.filter(follower=request.user)]

    return render(request, 'main/index.html', {
        'posts': posts,
        'form': form,
        'following_users': following_users  # 👈 передаём явно
    })



@login_required
def post_detail(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            post.comments.create(user=request.user, content=content)

        # Возврат обратно на ленту после отправки комментария
        return redirect('index')

    # Если всё же кто-то зайдёт на detail вручную — отрисуем комментарии
    return render(request, 'main/post_detail.html', {
        'post': post,
        'comments': post.comments.all()
    })


@login_required
def like_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    if request.user in post.likes.all():
        post.likes.remove(request.user)
    else:
        post.likes.add(request.user)
    return redirect('index')


@login_required
def follow_user(request, user_id):
    target = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        if Follow.objects.filter(follower=request.user, following=target).exists():
            Follow.objects.filter(follower=request.user, following=target).delete()
        else:
            Follow.objects.create(follower=request.user, following=target)

    return redirect('index')



@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)

    if comment.user == request.user:
        comment.delete()

    return redirect('post_detail', post_id=comment.post.id)

from django.http import HttpResponseForbidden

@login_required
def delete_post(request, post_id):
    post = get_object_or_404(Post, id=post_id)

    if post.author != request.user:
        return HttpResponseForbidden("You are not allowed to delete this post.")

    if request.method == 'POST':
        post.delete()
        return redirect('index')

    return render(request, 'main/confirm_delete.html', {'post': post})

