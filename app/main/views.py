from flask import render_template, redirect, url_for, abort, flash, request,\
    current_app, make_response, g
from flask_login import login_required, current_user
from flask_sqlalchemy import get_debug_queries
from sqlalchemy.sql import or_
from . import main
from .forms import EditProfileForm, EditProfileAdminForm, PostForm,\
    CommentForm, SearchForm, ApplyForm
from .. import db
from ..models import Permission, Role, User, Post, Comment, Book, Lend
from ..decorators import admin_required, permission_required


@main.after_app_request
def after_request(response):
    for query in get_debug_queries():
        if query.duration >= current_app.config['FLASKY_SLOW_DB_QUERY_TIME']:
            current_app.logger.warning(
                'Slow query: %s\nParameters: %s\nDuration: %fs\nContext: %s\n'
                % (query.statement, query.parameters, query.duration,
                   query.context))
    return response


@main.route('/shutdown')
def server_shutdown():
    if not current_app.testing:
        abort(404)
    shutdown = request.environ.get('werkzeug.server.shutdown')
    if not shutdown:
        abort(500)
    shutdown()
    return 'Shutting down...'


@main.route('/', methods=['GET', 'POST'])
def index():
    form = PostForm()
    if current_user.can(Permission.WRITE_ARTICLES) and \
            form.validate_on_submit():
        post = Post(body=form.body.data,
                    author=current_user._get_current_object())
        db.session.add(post)
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    show_followed = False
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get('show_followed', ''))
    if show_followed:
        query = current_user.followed_posts
    else:
        query = Post.query
    pagination = query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items

    lends = Lend.query.all()
    return render_template('index.html',
                           form=form, posts=posts,show_followed=show_followed, pagination=pagination,
                           lends=lends)


@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    # pagination = user.posts.order_by(Post.timestamp.desc()).paginate(
    #     page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
    #     error_out=False)
    # posts = pagination.items
    query = Lend.query.filter_by(lender_id=user.id)
    pagination = query.order_by(Lend.id.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    lends = pagination.items
    return render_template('user.html', user=user, lends=lends,
                           pagination=pagination)

@main.route('/book/<book_isbn>')
def book(book_isbn):
    #评论部分
    form = PostForm()
    if current_user.can(Permission.WRITE_ARTICLES) and \
            form.validate_on_submit():
        post = Post(body=form.body.data,
                    author=current_user._get_current_object())
        db.session.add(post)
        return redirect(url_for('.book'))
    page = request.args.get('page', 1, type=int)
    show_followed = False
    if current_user.is_authenticated:
        show_followed = bool(request.cookies.get('show_followed', ''))
    if show_followed:
        query = current_user.followed_posts
    else:
        query = Post.query
    pagination = query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    ##############

    book = Book.query.filter_by(ISBN=book_isbn).first_or_404()
    # lends = Lend.query.filter_by(book_id=book.id).first()
    notborrowed_book = Lend.query.filter(Lend.borrowed==0,Lend.book_id==book.id).filter(or_(Lend.borrower_id==0,Lend.borrower_id==None)).all()
    borrowed_book = Lend.query.filter_by(borrowed=1,book_id=book.id).all()

    return render_template('book.html',
                           posts=posts,show_followed=show_followed, pagination=pagination,form=form,
                           book=book, notborrowed_book=notborrowed_book, borrowed_book=borrowed_book)

@main.route('/bookshop')
def bookshop():
    #已经被借的书和还未被借的书分开
    notborrowed_book = Lend.query.filter(Lend.borrowed==0).filter(or_(Lend.borrower_id==0, Lend.borrower_id==None)).all()
    borrowed_book = Lend.query.filter_by(borrowed=1).all()
    return render_template('bookshop.html', notborrowed_book=notborrowed_book, borrowed_book=borrowed_book)

@main.route('/lend', methods=['GET', 'POST'])
def lend():
    return render_template('lend.html',form=g.search_form)

@main.route('/search', methods=['GET', 'POST'])
# @login_required
def search():
    if not g.search_form.validate_on_submit():
         return redirect(url_for('.lend'))
    return redirect(url_for('.search_results',query=g.search_form.search.data))

@main.route('/search_results/<query>')
# @login_required
def search_results(query):
    results = Book.query.filter(Book.ISBN.ilike(query)|Book.bookname.ilike('%'+query+'%')|Book.author.ilike('%'+query+'%')).all()
    return render_template('search_results.html',
    query = query,
    results = results)

#lends_id是借阅表的id，用来确定借的是哪本书以及出借者是谁
@main.route('/order/<lends_id>', methods=['GET', 'POST'])
@login_required
def order(lends_id):
    lend = Lend.query.filter_by(id=lends_id).first()
    #被借->空闲
    if lend.borrowed:
        lend.borrower_id = None
        lend.borrowed = not lend.borrowed
        db.session.add(lend)
    # 空闲->被借
    else:
        # lend.borrowed = not lend.borrowed
        lend.borrower_id = current_user.id
        db.session.add(lend)
    return redirect(url_for('.user_order',show_lend='2'))



@main.route('/apply/<book_isbn>',methods=['GET', 'POST'])
@login_required
def apply(book_isbn):
    form = ApplyForm()
    book = Book.query.filter_by(ISBN = book_isbn).first()
    if form.validate_on_submit():
        lend = Lend(book_id = book.id,lender_id = current_user.id,borrowed=0,received=0)
        db.session.add(lend)
        return redirect(url_for('.bookshop'))
    return render_template('apply.html',book=book,form=form)

@main.route('/user-order', methods=['GET', 'POST'])
@login_required
def user_order():
    show_lend = 0
    if current_user.is_authenticated:
        # show_lend = bool(request.cookies.get('show_lend', ''))
        show_lend = str(request.cookies.get('show_lend', '0'))
    if show_lend == '0':
        #show_lend等于0，即借入订单，需要找到借入人是用户本身且已经通过申请的订单
        lends = Lend.query.filter_by(borrower_id=current_user.id, borrowed=1).all()
    elif show_lend == '1':
        # show_lend等于1，即借出订单，需要找到出借人是用户本身且已经通过申请的订单
        lends = Lend.query.filter_by(lender_id=current_user.id, borrowed=1).all()
    else:
        # 剩下的即show_lend等于2，申请列表，需要找到出借人或者申请者是用户本身且还未通过申请的订单
        # lends = Lend.query.filter_by(borrower_id=current_user.id, received=0)
        lends = Lend.query.filter(or_(Lend.lender_id == current_user.id,Lend.borrower_id == current_user.id)).filter(Lend.borrowed==0).all()
    return render_template('user_order.html', show_lend=show_lend, lends=lends)

@main.route('/borrowed-order')
@login_required
def show_borrowed_order():
    resp = make_response(redirect(url_for('.user_order')))
    resp.set_cookie('show_lend', '0', max_age=30*24*60*60)
    return resp

@main.route('/lend-order')
@login_required
def show_lend_order():
    resp = make_response(redirect(url_for('.user_order')))
    resp.set_cookie('show_lend', '1', max_age=30*24*60*60)
    return resp

@main.route('/ordering')
@login_required
def show_ordering():
    resp = make_response(redirect(url_for('.user_order')))
    resp.set_cookie('show_lend', '2', max_age=30*24*60*60)
    return resp

@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        flash('Your profile has been updated.')
        return redirect(url_for('.user', username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)


@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        flash('The profile has been updated.')
        return redirect(url_for('.user', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)


@main.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
    post = Post.query.get_or_404(id)
    form = CommentForm()
    if form.validate_on_submit():
        comment = Comment(body=form.body.data,
                          post=post,
                          author=current_user._get_current_object())
        db.session.add(comment)
        flash('Your comment has been published.')
        return redirect(url_for('.post', id=post.id, page=-1))
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (post.comments.count() - 1) // \
            current_app.config['FLASKY_COMMENTS_PER_PAGE'] + 1
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('post.html', posts=[post], form=form,
                           comments=comments, pagination=pagination)


@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author and \
            not current_user.can(Permission.ADMINISTER):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        db.session.add(post)
        flash('The post has been updated.')
        return redirect(url_for('.post', id=post.id))
    form.body.data = post.body
    return render_template('edit_post.html', form=form)


@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if current_user.is_following(user):
        flash('You are already following this user.')
        return redirect(url_for('.user', username=username))
    current_user.follow(user)
    flash('You are now following %s.' % username)
    return redirect(url_for('.user', username=username))


@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    if not current_user.is_following(user):
        flash('You are not following this user.')
        return redirect(url_for('.user', username=username))
    current_user.unfollow(user)
    flash('You are not following %s anymore.' % username)
    return redirect(url_for('.user', username=username))


@main.route('/followers/<username>')
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followers.paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.follower, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followers of",
                           endpoint='.followers', pagination=pagination,
                           follows=follows)


@main.route('/followed-by/<username>')
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('Invalid user.')
        return redirect(url_for('.index'))
    page = request.args.get('page', 1, type=int)
    pagination = user.followed.paginate(
        page, per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],
        error_out=False)
    follows = [{'user': item.followed, 'timestamp': item.timestamp}
               for item in pagination.items]
    return render_template('followers.html', user=user, title="Followed by",
                           endpoint='.followed_by', pagination=pagination,
                           follows=follows)


@main.route('/all')
@login_required
def show_all():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '', max_age=30*24*60*60)
    return resp


@main.route('/followed')
@login_required
def show_followed():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed', '1', max_age=30*24*60*60)
    return resp


@main.route('/moderate')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate():
    page = request.args.get('page', 1, type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page, per_page=current_app.config['FLASKY_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    return render_template('moderate.html', comments=comments,
                           pagination=pagination, page=page)


@main.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))


@main.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)))
