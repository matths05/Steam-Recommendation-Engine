from .recommender import build_tag_vocab, build_training_data, user_to_vector
from .models import User

def train_model():
    vocab = build_tag_vocab()
    user_ids, _ = build_training_data(vocab)

    for uid in user_ids:
        u = User.objects(id=uid).first()
        if u:
            u.calculated_vector = user_to_vector(u, vocab)
            u.save()
