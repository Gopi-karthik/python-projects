from flask import Flask, render_template, redirect, url_for, flash, request
from functools import wraps
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm,RegisterForm,LoginForm,CommentForm
from flask_gravatar import Gravatar

login_manager=LoginManager()
def admin_required(f):
    @wraps(f)
    def decorated_function(*args,**kwargs):
        if current_user.get_id()=='1':
            return f(*args,**kwargs)
        return "<h2>Forbidden page</h2>" \
               "<p>you don't have permission to enter this pages</p>"
    return decorated_function

app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)
login_manager.init_app(app)


gravatar = Gravatar(app,
                    size=100,
                    rating='g',
                    default='retro',
                    force_default=False,
                    force_lower=False,
                    use_ssl=False,
                    base_url=None)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)



##CONFIGURE TABLES


class UserRegister(db.Model,UserMixin):
    __tablename__='user_data'
    id=db.Column(db.Integer,primary_key=True)

    name=db.Column(db.String(200),nullable=False)
    email=db.Column(db.String(200),nullable=False,unique=True)
    password=db.Column(db.String(100),nullable=False)
    blogs = relationship('BlogPost', back_populates='author')
    user_comment=relationship("Comment",back_populates='comment_author')
    # def __str__(self):
    #     return self.name
with app.app_context():
   db.create_all()


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author_id=db.Column(db.Integer, db.ForeignKey('user_data.id'))
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    author =relationship("UserRegister", back_populates="blogs")
    blog_comment=relationship('Comment')
with app.app_context():
   db.create_all()

class Comment(db.Model):
    __tablename__='comments'
    id=db.Column(db.Integer,primary_key=True)
    author_id=db.Column(db.Integer,db.ForeignKey('user_data.id'))
    author=db.Column(db.String(100), nullable=False)
    comment_author=relationship("UserRegister",back_populates='user_comment')
    comment=db.Column(db.Text,nullable=False)
    blog_id=db.Column(db.Integer,db.ForeignKey('blog_posts.id'))
    parent_post=relationship('BlogPost',back_populates='blog_comment')
db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return UserRegister.query.get(user_id)
@app.route('/')
def get_all_posts():
    admin=False
    posts = BlogPost.query.all()

    if current_user.get_id()=='1':

        admin=True

    return render_template("index.html", all_posts=posts,admin=admin)


@app.route('/register',methods=['post','get'])
def register():

    if request.method=='POST':
       email=request.form['email']
       user=UserRegister.query.filter_by(email=request.form['email']).first()
       if user== None:

           password = generate_password_hash(request.form['password'], method="pbkdf2:sha256", salt_length=8)

           user=UserRegister(
               name=request.form['name'],
               email=email,
               password=password
           )
           print('hi')
           db.session.add(user)
           db.session.commit()
           return redirect(url_for('get_all_posts'))
       else:
           flash('you have already are the user please login')
           return redirect(url_for('login'))
    form =RegisterForm()
    return render_template("register.html",form=form)


@app.route('/login',methods=['POST','GET'])
def login():
    if request.method=='POST':
        user=UserRegister.query.filter_by(email=request.form['email']).first()
        if user==None:
            flash('The email id is invalid')
        else:
            if check_password_hash(user.password,request.form['password']):
                login_user(user)
                return redirect(url_for('get_all_posts'))
            else:
                flash('the password is incorrect')


    form=LoginForm()

    return render_template("login.html",form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>",methods=['GET',"POST"])
def show_post(post_id):
    admin=False
    requested_post = BlogPost.query.get(post_id)
    comment=CommentForm()
    if current_user.get_id()=='1':
        admin=True
    if comment.validate_on_submit():
        new_comment=Comment(
            comment=comment.comment.data,
            blog_id=post_id,
            author_id=current_user.get_id(),
            author=current_user.name
        )
        db.session.add(new_comment)
        db.session.commit()
    comments=Comment.query.filter_by(blog_id=post_id)

    return render_template("post.html", post=requested_post,admin=admin,comment=comment,comments=comments)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post",methods=['GET','POST'])
@admin_required
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        # print(request.form)
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        with app.app_context():
            db.session.add(new_post)
            db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>",methods=['POST',"GET"])
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000,debug=True)
