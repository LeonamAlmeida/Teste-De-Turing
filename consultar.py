# arquivo será removido no futuro
from pyravendb.store.document_store import DocumentStore

class UserDocument:
    def __init__(self, username, history, total, correct, accuracy):
        self.Username = username
        self.History = history
        self.Total = total
        self.Correct = correct
        self.Accuracy = accuracy

# Inicialize o DocumentStore
store = DocumentStore(urls=["http://localhost:8080"], database="Redes1")
store.initialize()

with store.open_session() as session:
    # Consulta onde o campo Username é igual a "Pedro"
    query_result = list(session.query(UserDocument).where_equals("Username", "PedroGore"))
    for doc in query_result:
        print(f"Username: {doc.Username}, Total: {doc.Total}, Correct: {doc.Correct}, Accuracy: {doc.Accuracy}")
