import os
import socket
import sys
import time
import threading
import requests
from collections import defaultdict
import json
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

store = DocumentStore(urls=["http://localhost:8080"], database="Redes1")
store.initialize()

HOST = '127.0.0.1'
PORT = 20000
BUFFER_SIZE = 1024

history = []
user_stats = defaultdict(lambda: {"total": 0, "correct": 0})

# Diretório do script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Diretório específico para salvar arquivos JSON dos usuários
USER_DATA_DIR = os.path.join(BASE_DIR, "user_data")

# Criar a pasta "user_data" se não existir
if not os.path.exists(USER_DATA_DIR):
    os.makedirs(USER_DATA_DIR)

# Caminho base para os arquivos JSON de cada usuário
def get_user_file(username):
    return os.path.join(USER_DATA_DIR, f"{username}.json")

def call_gpt_api(user_input):
    url = "https://chatgpt-42.p.rapidapi.com/conversationgpt4-2"
    user_input = f"{user_input}\nPor favor responda de maneira sucinta, da forma mais aproximada a uma resposta humana"
    headers = {
        "x-rapidapi-key": "11a7f49ecbmsh32f82601c876a89p18456djsn1fec454f8b02",
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
    user_file = get_user_file(username)
    user_data = {
        "username": username,
        "history": [],
        "total": 0,
        "correct": 0,
        "accuracy": 0.0
    }
    if os.path.exists(user_file):
        with open(user_file, "r", encoding="utf-8") as file:
            user_data = json.load(file)
    user_data["history"].append({
        "question": user_input,
        "response": response,
        "choice": choice,
        "correct": correct
    })
    user_data["total"] += 1
    if correct:
        user_data["correct"] += 1
    user_data["accuracy"] = (user_data["correct"] / user_data["total"]) * 100 if user_data["total"] > 0 else 0

    user_document = UserDocument(
        username=user_data["username"],
        history=user_data["history"],
        total=user_data["total"],
        correct=user_data["correct"],
        accuracy=user_data["accuracy"]
    )

    with store.open_session() as session:
        session.store(user_document)
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
        self.root = root
        self.root.title("Servidor TCP")
        
        self.mode = ttk.StringVar(value="automatico")
        self.delay = ttk.IntVar(value=1)
        self.server_thread = None
        self.is_running = False
        self.current_client_socket = None
        self.current_user_input = None

        self.create_widgets()
    
    def create_widgets(self):
        config_frame = ttk.Frame(self.root, padding=10)
        config_frame.grid(row=0, column=0, sticky=(N, S, E, W))

        ttk.Label(config_frame, text="Modo de Operação:").grid(row=0, column=0, padx=5, pady=5, sticky=W)
        ttk.Radiobutton(config_frame, text="Automático", variable=self.mode, value="automatico").grid(row=0, column=1, padx=5, pady=5, sticky=W)
        ttk.Radiobutton(config_frame, text="Controlado", variable=self.mode, value="controlado").grid(row=0, column=2, padx=5, pady=5, sticky=W)

        ttk.Label(config_frame, text="Tempo de Espera (segundos):").grid(row=1, column=0, padx=5, pady=5, sticky=W)
        ttk.Entry(config_frame, textvariable=self.delay, width=5).grid(row=1, column=1, padx=5, pady=5, sticky=W)

        self.start_button = ttk.Button(config_frame, text="Iniciar Servidor", command=self.start_server, bootstyle=SUCCESS)
        self.start_button.grid(row=2, column=0, padx=5, pady=5, sticky=W)

        self.stop_button = ttk.Button(config_frame, text="Parar Servidor", command=self.stop_server, bootstyle=DANGER, state=DISABLED)
        self.stop_button.grid(row=2, column=1, padx=5, pady=5, sticky=W)

        self.log_text = ttk.Text(self.root, wrap='word', height=20, width=80)
        self.log_text.grid(row=1, column=0, padx=10, pady=10)

        self.manual_frame = ttk.Frame(self.root, padding=10)
        self.manual_response = ttk.Entry(self.manual_frame, width=50)
        self.manual_send_button = ttk.Button(self.manual_frame, text="Enviar Resposta", command=self.send_manual_response, bootstyle=PRIMARY)
        self.manual_response.grid(row=0, column=0, padx=5, pady=5)
        self.manual_send_button.grid(row=0, column=1, padx=5, pady=5)
        self.manual_frame.grid(row=2, column=0, padx=10, pady=10)
        self.manual_frame.grid_forget()

        self.choice_frame = ttk.Frame(self.root, padding=10)
        ttk.Label(self.choice_frame, text="Escolha entre IA e manual:").grid(row=0, column=0, padx=5, pady=5, sticky=W)
        self.choice_var = ttk.StringVar(value="ia")
        ttk.Radiobutton(self.choice_frame, text="IA", variable=self.choice_var, value="ia").grid(row=1, column=0, padx=5, pady=5, sticky=W)
        ttk.Radiobutton(self.choice_frame, text="Manual", variable=self.choice_var, value="manual").grid(row=1, column=1, padx=5, pady=5, sticky=W)
        self.choice_button = ttk.Button(self.choice_frame, text="Enviar Escolha", command=self.send_choice, bootstyle=PRIMARY)
        self.choice_button.grid(row=2, column=0, columnspan=2, pady=5)

        self.choice_frame.grid_forget()

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
        self.log("Escolha: IA ou manual")
        self.choice_frame.grid(row=2, column=0, padx=10, pady=10)
        self.choice_button.configure(command=lambda: self.process_choice(user_input, client_socket,username,delay))
        self.current_client_socket = client_socket
        self.current_user_input = user_input

    def send_choice(self):
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
            self.manual_send_button.configure(command=lambda: self.send_manual_response(user_input, client_socket,username))
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

                
if __name__ == "__main__":
    root = ttk.Window(themename="superhero")
    app = ServerGUI(root)
    root.mainloop()
