import socket
import time
import threading
import requests
from collections import defaultdict
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from pyravendb.store.document_store import DocumentStore

class UserDocument:
    def __init__(self, username, history, total, correct, accuracy):
        self.Username = username
        self.History = history
        self.Total = total
        self.Correct = correct
        self.Accuracy = accuracy

store = DocumentStore(urls=["http://localhost:8080"], database="BD2")
store.initialize()

HOST = '127.0.0.1'
PORT = 20000
BUFFER_SIZE = 1024

history = []
user_stats = defaultdict(lambda: {"total": 0, "correct": 0})

def call_gpt_api(user_input):
    url = "https://chatgpt-42.p.rapidapi.com/conversationgpt4-2"
    user_input = f"{user_input}\nPor favor responda de maneira sucinta, da forma mais aproximada a uma resposta humana"
    headers = {
        "x-rapidapi-key": "63e0dc075bmshc19cabf8603f7abp1d53bdjsnf8ff1645091f",
        "x-rapidapi-host": "chatgpt-42.p.rapidapi.com",
        "Content-Type": "application/json"
    }
    payload = {
        "messages": [{"role": "user", "content": user_input}],
        "system_prompt": "",
        "temperature": 0.9,
        "top_k": 5,
        "top_p": 0.9,
        "max_tokens": 256,
        "web_access": False
    }
    response = requests.post(url, headers=headers, json=payload)
    result = response.json().get("result")
    return result

def save_user_data_ravendb(username, user_input, response, choice, correct):
    with store.open_session() as session:
        # Tentar carregar o documento do usuário no RavenDB
        user_document = session.load(f"users/{username}")

        # Se o documento não existir, inicializa os dados
        if user_document is None:
            user_document = UserDocument(
                username=username,
                history=[],
                total=0,
                correct=0,
                accuracy=0.0
            )

        # Atualiza os dados do usuário
        user_document.History.append({
            "question": user_input,
            "response": response,
            "choice": choice,
            "correct": correct
        })
        user_document.Total += 1
        if correct:
            user_document.Correct += 1
        user_document.Accuracy = (user_document.Correct / user_document.Total) * 100 if user_document.Total > 0 else 0

        # Salvar ou atualizar o documento no RavenDB
        session.store(user_document, f"users/{username}")
        session.save_changes()

    print("Dados do usuário armazenados com sucesso no RavenDB.")

def save_user_data(username, user_input, response, choice, correct):
    save_user_data_ravendb(username, user_input, response, choice, correct)

def on_new_client(clientsocket, addr, mode, delay, username):
    try:
        while True:
            data = clientsocket.recv(BUFFER_SIZE)
            if not data:
                print(f'Conexão fechada pelo cliente {addr[0]}.')
                break
            user_input = data.decode('utf-8').strip()
            app.log(f"Pergunta: {user_input}")

            if mode == "automatico":
                time.sleep(delay)
                response = call_gpt_api(user_input)
                if clientsocket and not clientsocket._closed:
                    clientsocket.send(response.encode('utf-8'))
                    app.log(f"Resposta da IA para {username}: {response}")

                    choice = clientsocket.recv(BUFFER_SIZE).decode('utf-8').strip()
                    correct = (choice == "ia")

                    history.append({
                        "username": username,
                        "question": user_input,
                        "response": response,
                        "choice": choice,
                        "correct": correct
                    })
                    user_stats[username]["total"] += 1
                    if correct:
                        user_stats[username]["correct"] += 1

                    save_user_data(username, user_input, response, choice, correct)

                    feedback = "Correto!" if correct else "Incorreto!"
                    clientsocket.send(feedback.encode('utf-8'))

            elif mode == "controlado":
                app.show_choice_message(user_input, clientsocket, username, delay)
                break

    except Exception as error:
        print("Erro na conexão com o cliente!")
        print(error)

class ServerGUI:
    def __init__(self, root):
        self.quantidade_de_perguntas_dados = 0
        self.respostas_corretas_dados = 0
        self.precisao_dados = None

        self.root = root
        self.root.title("Servidor TCP")
        
        self.mode = ttk.StringVar(value="automatico")
        self.delay = ttk.IntVar(value=1)
        self.server_thread = None
        self.is_running = False
        self.current_client_socket = None
        self.current_user_input = None

        self.create_widgets()
        
        # Adiciona um frame para o perfil
        self.perfil_frame = ttk.Frame(self.root, padding=10)
        self.create_perfil_frame()

    def create_widgets(self):
        self.config_frame = ttk.Frame(self.root, padding=10)
        self.config_frame.grid(row=0, column=0, sticky=(N, S, E, W))

        ttk.Label(self.config_frame, text="Modo de Operação:").grid(row=0, column=0, padx=5, pady=5, sticky=W)
        ttk.Radiobutton(self.config_frame, text="Automático", variable=self.mode, value="automatico").grid(row=0, column=1, padx=5, pady=5, sticky=W)
        ttk.Radiobutton(self.config_frame, text="Controlado", variable=self.mode, value="controlado").grid(row=0, column=2, padx=5, pady=5, sticky=W)

        ttk.Label(self.config_frame, text="Tempo de Espera (segundos):").grid(row=1, column=0, padx=5, pady=5, sticky=W)
        ttk.Entry(self.config_frame, textvariable=self.delay, width=5).grid(row=1, column=1, padx=5, pady=5, sticky=W)

        self.start_button = ttk.Button(self.config_frame, text="Iniciar Servidor", command=self.start_server, bootstyle=SUCCESS)
        self.start_button.grid(row=2, column=0, padx=5, pady=5, sticky=W)

        self.stop_button = ttk.Button(self.config_frame, text="Parar Servidor", command=self.stop_server, bootstyle=DANGER, state=DISABLED)
        self.stop_button.grid(row=2, column=1, padx=5, pady=5, sticky=W)

        self.perfil_buttom = ttk.Button(self.config_frame, state=NORMAL, text="Gerenciar BD", style="primary.TButton",width=12, command=lambda: self.show_perfil())
        self.perfil_buttom.grid(row=2, column=3, padx=5, pady=5, sticky=W)

        self.log_text = ttk.Text(self.root, wrap='word', height=20, width=80)
        self.log_text.grid(row=1, column=0, padx=10, pady=10)

        self.manual_frame = ttk.Frame(self.root, padding=10)
        self.manual_response = ttk.Entry(self.manual_frame, width=50)
        self.manual_send_button = ttk.Button(self.manual_frame, text="Enviar Resposta", command=self.send_manual_response, bootstyle=PRIMARY, state=DISABLED)
        self.manual_response.grid(row=0, column=0, padx=5, pady=5)
        self.manual_send_button.grid(row=0, column=1, padx=5, pady=5)
        self.manual_frame.grid(row=3, column=0, padx=10, pady=10)

        self.choice_frame = ttk.Frame(self.root, padding=10)
        ttk.Label(self.choice_frame, text="Escolha entre IA e manual:").grid(row=0, column=0, padx=5, pady=5, sticky=W)
        self.choice_var = ttk.StringVar(value="ia")
        ttk.Radiobutton(self.choice_frame, text="IA", variable=self.choice_var, value="ia").grid(row=1, column=0, padx=5, pady=5, sticky=W)
        ttk.Radiobutton(self.choice_frame, text="Manual", variable=self.choice_var, value="manual").grid(row=1, column=1, padx=5, pady=5, sticky=W)
        self.choice_button = ttk.Button(self.choice_frame, text="Enviar Escolha", command=self.send_choice, bootstyle=PRIMARY, state=DISABLED)
        self.choice_button.grid(row=2, column=0, columnspan=2, pady=5)
        self.choice_frame.grid(row=2, column=0, padx=10, pady=10)

    def create_perfil_frame(self):
        self.username_var = ttk.StringVar()
        self.username = None
        self.document_id = None

        self.voltar_button = ttk.Button(self.perfil_frame, text="Voltar", command=self.show_main)
        self.voltar_button.grid(row=7, column=5, padx=5, pady=5)

        # Área que irá definir os frames do perfil
        frame_perfil_1 = ttk.Frame(self.perfil_frame)
        frame_perfil_1.grid(row=0, column=0,pady=10, padx=10)

        #Frame de nome de pesquisa
        ttk.Label(frame_perfil_1, text="Nome:             ", font=("Arial", 12)).pack(side=LEFT, padx=5)
        self.username_entry = ttk.Entry(frame_perfil_1, textvariable=self.username_var, width=30, font=("Arial", 12))
        self.username_entry.pack(side=LEFT, fill=X, expand=TRUE, padx=5)

        #frame de impressão de usuários por precisão
        frame_perfil_2 = ttk.Frame(self.perfil_frame)
        frame_perfil_2.grid(row=1, column=0,pady=10, padx=10)

        self.pesquisa_por_presicao_mais_50 = ttk.Button(frame_perfil_2, text="Precisão >= 50%", command=lambda: self.imprime_users_com_precisao_maior_que_50(), bootstyle=SUCCESS)
        self.pesquisa_por_presicao_mais_50.pack(side=RIGHT, padx=10)

        self.pesquisa_por_presicao_menos_50 = ttk.Button(frame_perfil_2, text="Precisão < 50%", command=lambda: self.imprime_users_com_precisao_menor_que_50(), bootstyle=SUCCESS)
        self.pesquisa_por_presicao_menos_50.pack(side=RIGHT, padx=10)

        #frames das labels
        frame_perfil_3 = ttk.Frame(self.perfil_frame)
        frame_perfil_3.grid(row=2, column=0,pady=10, padx=10)

        data_text = ttk.Text(frame_perfil_3, height=20, width=83, font=("Arial", 12))  # Aumentando a largura para 80
        data_text.pack(padx=5)

        self.historico_text = ttk.Text(data_text, height=20, width=83, font=("Arial", 12))  # Aumentando a largura para 80
        self.historico_text.pack(padx=5)

        self.quantidade_de_perguntas = ttk.Label(frame_perfil_3, text=f"Quantidade de perguntas: {0}", font=("Arial", 12))
        self.quantidade_de_perguntas.pack(side=LEFT, padx=10)
        self.respostas_corretas = ttk.Label(frame_perfil_3, text=f"Acertos: {0}", font=("Arial", 12))
        self.respostas_corretas.pack(side=LEFT, padx=10)
        self.precisao = ttk.Label(frame_perfil_3, text=f"Precisão: {0}%", font=("Arial", 12))
        self.precisao.pack(side=LEFT, padx=10)

        #Botões de opções
        self.pesquisa = ttk.Button(frame_perfil_1, text="Pesquisar", command=lambda: self.pesquisa_user(), bootstyle=SUCCESS)
        self.pesquisa.pack(side=RIGHT, padx=10)

        self.delete = ttk.Button(frame_perfil_1, text="Deletar", command=lambda: self.deleta_user(self.username), bootstyle=SUCCESS, state=DISABLED)

        self.delete = ttk.Button(frame_perfil_1, text="Deletar", command=lambda: self.deleta_user(self.username), bootstyle=SUCCESS)

        self.delete.pack(side=RIGHT, padx=10)

    def pesquisa_user(self):
        self.username = self.username_var.get()

        document = self.consulta_documento(self.username)
        quantidade_de_perguntas_dados = self.retorna_quantidade_perguntas(document)
        respostas_corretas_dados = self.retorna_quantidade_acertos(document)
        precisao_dados = self.retorna_precisao(document)
        historico = self.retorna_user_log(document)

        document = self.consulta_documento(self.username)
        quantidade_de_perguntas_dados = self.retorna_quantidade_perguntas(document)
        respostas_corretas_dados = self.retorna_quantidade_acertos(document)
        precisao_dados = self.retorna_precisao(document)
        historico = self.retorna_user_log(document)

        # Atualizando o texto do Label para refletir a nova quantidade de perguntas
        self.quantidade_de_perguntas.config(text=f"Quantidade de perguntas: {quantidade_de_perguntas_dados}")

        self.respostas_corretas.config(text=f"Acertos: {respostas_corretas_dados}")

        self.precisao.config(text=f"Precisão: {precisao_dados:.2f}%")

        self.historico_text.delete("1.0", END)
        self.historico_text.insert(END, historico)

        self.delete.configure(state=NORMAL)

    #Recupera o documento com o nome do user atual
    def consulta_documento(self, username):
        document = None

        with store.open_session() as session:
            query_result = list(session.query(UserDocument).where_equals("Username", username))

            #Se houver retorno query result será do tipo lista
            if len(query_result)>0:
                for doc in query_result:
                    document = doc
                    self.document_id = session.advanced.get_document_id(document)
            else:
                document = None

            return document

    def retorna_quantidade_perguntas(self, document):
        if document == None:
            return 0
        return document.Total

    def retorna_quantidade_acertos(self, document):
        if document == None:
            return 0
        return document.Correct

    def retorna_precisao(self, document):
        if document == None:
            return 0
        return document.Accuracy

    def retorna_user_log(self, document):
        if document == None:
            return ""
        history = document.History
        formated_history = "" 
        for i in range(len(history)):
            history_aux = dict(history[i])
            formated_history += f"Pergunta {i+1}:\n{history_aux['question']}\n\nResposta:\n{history_aux['response']}\n\nAcertou: {history_aux['correct']}"
            formated_history += "\n_______________________________________________________________________________\n"
            
        return formated_history
    
    def deleta_user(self, username):
        try:
            with store.open_session() as session:
                if self.document_id!=None:
                    session.delete(self.document_id)  # Exclui o documento
                    session.save_changes()  # Salva as alterações no banco

                    self.historico_text.delete("1.0", END)
                    self.historico_text.insert(END, f"User {username} deletado")
            self.delete.configure(state=DISABLED)

            self.historico_text.delete("1.0", END)
            self.historico_text.insert(END, f"User {username} deletado")

        except Exception as error:
            print(error)

    def imprime_users_com_precisao_maior_que_50(self):
        with store.open_session() as session:
            query_result = list(session.query(UserDocument).where_greater_than_or_equal("Accuracy", 50))

            users = ""
            #Se houver retorno query result será do tipo lista
            if len(query_result)>0:
                for doc in query_result:
                    users += f"User: {doc.Username}, Precisão: {doc.Accuracy}\n"
            else:
                users = "Nenhum participante com (50%) ou mais de precisão"

            self.historico_text.delete("1.0", END)
            self.historico_text.insert(END, users)

    def imprime_users_com_precisao_menor_que_50(self):
        with store.open_session() as session:
            query_result = list(session.query(UserDocument).where_less_than("Accuracy", 50))

            users = ""
            #Se houver retorno query result será do tipo lista
            if len(query_result)>0:
                for doc in query_result:
                    users += f"User: {doc.Username}, Precisão: {doc.Accuracy}\n"
            else:
                users = "Nenhum participante com menos de (50%) de precisão"

            self.historico_text.delete("1.0", END)
            self.historico_text.insert(END, users)

    def show_perfil(self):
        # Esconde os widgets da interface principal
        self.config_frame.grid_forget()
        self.log_text.grid_forget()
        self.manual_frame.grid_forget()
        self.choice_frame.grid_forget()
        # Exibe o frame do perfil
        self.perfil_frame.grid(row=1, column=0, padx=10, pady=10)

    def show_main(self):
        # Esconde o frame do perfil
        self.perfil_frame.grid_forget()

        # Exibe os widgets da interface principal novamente
        self.config_frame.grid(row=0, column=0, sticky=(N, S, E, W))
        self.log_text.grid(row=1, column=0, padx=10, pady=10)
        self.manual_response.grid(row=0, column=0, padx=5, pady=5)
        self.manual_send_button.grid(row=0, column=1, padx=5, pady=5)
        self.manual_frame.grid(row=3, column=0, padx=10, pady=10)
        self.choice_frame.grid(row=2, column=0, padx=10, pady=10)

    def start_server(self):
        self.is_running = True
        self.server_thread = threading.Thread(target=self.run_server)
        self.server_thread.start()
        self.start_button.configure(state=DISABLED)
        self.stop_button.configure(state=NORMAL)

    def run_server(self):
        mode = self.mode.get()
        delay = self.delay.get()
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
                server_socket.bind((HOST, PORT))
                server_socket.listen()
                self.log("Servidor escutando em {}:{}".format(HOST, PORT))
                while self.is_running:
                    clientsocket, addr = server_socket.accept()
                    username = clientsocket.recv(BUFFER_SIZE).decode('utf-8').strip()
                    self.log(f'{username} conectou ao servidor.')

                    t = threading.Thread(target=on_new_client, args=(clientsocket, addr, mode, delay, username))
                    t.start()
        except Exception as error:
            self.log("Erro na execução do servidor!")
            self.log(str(error))

    def stop_server(self):
        self.is_running = False
        self.start_button.configure(state=DISABLED)
        self.stop_button.configure(state=DISABLED)
        self.log("Servidor Parado.")

    def log(self, message):
        self.log_text.insert(END, message + "\n")
        self.log_text.see(END)

    def show_choice_message(self, user_input, client_socket,username,delay):
        self.choice_button.configure(state=NORMAL)
        self.log("Escolha: IA ou manual")
        self.choice_frame.grid(row=2, column=0, padx=10, pady=10)
        self.choice_button.configure(command=lambda: self.process_choice(user_input, client_socket,username,delay))
        self.current_client_socket = client_socket
        self.current_user_input = user_input

    def send_choice(self):
        self.choice_button.configure(state=DISABLED)
        self.manual_send_button.configure(state=NORMAL)
        choice = self.choice_var.get().strip()
        self.log(f"Enviando escolha: {choice}")  # Adicione esta linha
        if choice:
            if self.current_client_socket and not self.current_client_socket._closed:
                self.current_client_socket.send(choice.encode('utf-8'))
                self.choice_frame.grid_forget()
                self.log(f"Escolha enviada: {choice}")

    def process_choice(self, user_input, client_socket,username,delay):
        choice = self.choice_var.get().strip()
        self.log(f"Processando escolha: {choice}")  # Adicione esta linha
        if choice == "manual":
            self.manual_frame.grid()  # Torna o frame de resposta manual visível
            self.manual_send_button.configure(state=NORMAL ,command=lambda: self.send_manual_response(user_input, client_socket,username))
            self.choice_button.configure(state=DISABLED)
        else:
            time.sleep(delay)
            if client_socket and not client_socket._closed:
                response = call_gpt_api(user_input)
                client_socket.send(response.encode('utf-8'))
                self.log(f"Resposta da IA para o cliente: {response}")
                
                choice = client_socket.recv(BUFFER_SIZE).decode('utf-8').strip()
                correct = (choice == "ia")
                history.append({
                    "username": username,
                    "question": user_input,
                    "response": response,
                    "choice": choice,
                    "correct": correct
                })
                user_stats[username]["total"] += 1
                if correct:
                    user_stats[username]["correct"] += 1

                save_user_data(username, user_input, response, choice, correct)

                feedback = "Correto!" if correct else "Incorreto!"
                client_socket.send(feedback.encode('utf-8'))                       
                    
    def send_manual_response(self, user_input, client_socket,username):

        response = self.manual_response.get().strip()
        if response:
            print(response)
            client_socket.send(response.encode('utf-8'))
            choice = client_socket.recv(BUFFER_SIZE).decode('utf-8').strip()
            correct = (choice == "humano")
            history.append({
                "username": username,
                "question": user_input,
                "response": response,
                "choice": choice,
                "correct": correct
            })
            user_stats[username]["total"] += 1
            if correct:
                user_stats[username]["correct"] += 1

            save_user_data(username, user_input, response, choice, correct)

            feedback = "Correto!" if correct else "Incorreto!"
            client_socket.send(feedback.encode('utf-8'))

            self.choice_button.configure(state=DISABLED)
            self.manual_send_button.configure(state=DISABLED)

if __name__ == "__main__":
    root = ttk.Window(themename="superhero")
    app = ServerGUI(root)
    root.mainloop()