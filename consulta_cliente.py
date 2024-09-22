from pyravendb.store.document_store import DocumentStore

class UserDocument:
    def __init__(self, username, history, total, correct, accuracy):
        self.Username = username
        self.History = history
        self.Total = total
        self.Correct = correct
        self.Accuracy = accuracy

# Inicialize o DocumentStore 
store = DocumentStore(urls=["http://localhost:8080"], database="BD2")
store.initialize()
document = None

#Recupera o documento com o nome do user atual
def consulta_documento(username):
    global document
    with store.open_session() as session:
        query_result = list(session.query(UserDocument).where_equals("Username", username))

        #Se houver retorno query result será do tipo lista
        if len(query_result)>0:
            for doc in query_result:
                document = doc
        else:
            document = None

def retorna_quantidade_perguntas():
    if document == None:
        return 0
    return document.Total

def retorna_quantidade_acertos():
    if document == None:
        return 0
    return document.Correct

def retorna_precisao():
    if document == None:
        return 0
    return document.Accuracy

def retorna_user_log():
    if document == None:
        return ""
    history = document.History
    formated_history = "" 
    for i in range(len(history)):
        history_aux = dict(history[i])
        formated_history += f"Pergunta {i+1}:\n{history_aux['question']}\n\nResposta:\n{history_aux['response']}\n\Acertou: {history_aux['correct']}"
        formated_history += "\n_______________________________________________________________________________\n"
        
    return formated_history