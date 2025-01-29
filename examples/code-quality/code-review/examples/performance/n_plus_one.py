from sqlalchemy import Column, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import Session, declarative_base, relationship

Base = declarative_base()


class User(Base):
    """User model."""

    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String)
    posts = relationship("Post", back_populates="user")


class Post(Base):
    """Post model."""

    __tablename__ = "posts"
    id = Column(Integer, primary_key=True)
    title = Column(String)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="posts")


def get_users_with_posts():
    """
    Retrieves all users and their posts.
    WARNING: This function has the N+1 query problem!
    """
    engine = create_engine("sqlite:///blog.db")
    session = Session(engine)

    # First query to get all users
    users = session.query(User).all()

    result = []
    # N+1 Problem: Making a separate query for each user's posts
    for user in users:
        posts = session.query(Post).filter(Post.user_id == user.id).all()
        result.append(
            {
                "username": user.username,
                "post_count": len(posts),
                "posts": [p.title for p in posts],
            }
        )

    return result


# Better solution would use JOIN or subquery:
# users_with_posts = session.query(User).options(joinedload(User.posts)).all()
