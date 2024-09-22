from pyravendb.store.document_store import DocumentStore
from pyravendb.commands.raven_commands import PutDocumentCommand
import random

# Definindo a classe de documento do usuário
class UserDocument:
    def __init__(self, username, history, total, correct, accuracy):
        self.Username = username
        self.History = history
        self.Total = total
        self.Correct = correct
        self.Accuracy = accuracy

# Conectar ao RavenDB
store = DocumentStore(urls=["http://localhost:8080"], database="BD2")
store.initialize()

# Função para gerar dados fictícios de usuários e interações
def generate_fake_data(username):
    questions = [
        "Você gosta de café?",
        "A Terra é redonda?",
        "Python é melhor que Java?",
        "Você prefere verão ou inverno?",
        "Inteligência artificial é o futuro?"
    ]

    responses = [
        "Sim", "Não", "Talvez", "Depende", "Com certeza!"
    ]

    history = []
    total = random.randint(5, 10)  # Número total de interações
    correct = 0

    for _ in range(total):
        question = random.choice(questions)
        response = random.choice(responses)
        choice = random.choice(["ia", "humano"])
        correct_choice = random.choice([True, False])
        if correct_choice:
            correct += 1

        history.append({
            "question": question,
            "response": response,
            "choice": choice,
            "correct": correct_choice
        })

    accuracy = (correct / total) * 100 if total > 0 else 0.0
    return UserDocument(username=username, history=history, total=total, correct=correct, accuracy=accuracy)

# Função para popular o banco de dados com os dados fictícios
def populate_database():
    usernames = [
    "alice", "bob", "charlie", "david", "eve", 
    "ana", "bruno", "camila", "daniel", "elisa",
    "amanda", "brian", "caio", "denise", "eric",
    "arthur", "bianca", "carla", "diana", "ethan",
    "antonio", "bruna", "claudio", "diego", "emily",
    "adam", "barbara", "carlos", "daphne", "edward",
    "alex", "bernardo", "carol", "dorothy", "enrique",
    "aline", "benjamin", "cecilia", "derek", "ellen",
    "andrew", "beatriz", "clara", "dominic", "esther",
    "alberto", "bryan", "claire", "dylan", "eliane"
]
    
    with store.open_session() as session:
        for username in usernames:
            user_document = generate_fake_data(username)
            session.store(user_document, f"users/{username}")
        session.save_changes()

    print("Banco de dados populado com sucesso!")

if __name__ == "__main__":
    populate_database()
