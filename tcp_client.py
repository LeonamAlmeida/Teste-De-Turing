import os
import socket
import threading
import consulta_cliente
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.style import Style
from tkinter import END, LEFT, X, StringVar, CENTER

HOST = '127.0.0.1'
PORT = 20000
BUFFER_SIZE = 1024

current_dir = os.path.dirname(os.path.abspath(__file__))

app = ttk.Window("Cliente TCP", themename="superhero")
app.geometry("800x600")
style = Style(theme="superhero")

username = StringVar()  # Variável para armazenar o nome de usuário
total_ia = 0
total_human = 0
correct_guesses = 0
s = None

quantidade_de_perguntas_dados = 0
precisao_dados = 0
respostas_corretas_dados = 0
user_log = ""

# Estilização da interface
label = ttk.Label(app, text="Cliente TCP", font=("Arial", 20, "bold"))
label.pack(pady=10)

# Frame para o nome do usuário
username_frame = ttk.Frame(app)
username_frame.pack(side="top", anchor="nw", padx=10, pady=10, fill=X)

#frameDePerfil
perfil_frame = ttk.Frame(app)

#Frame de login
ttk.Label(username_frame, text="Nome:             ", font=("Arial", 12)).pack(side=LEFT, padx=5)
username_entry = ttk.Entry(username_frame, textvariable=username, width=30, font=("Arial", 12))
username_entry.pack(side=LEFT, fill=X, expand=TRUE, padx=5)

send_username_button = ttk.Button(username_frame, text="Login", style="primary.TButton",width=6, command=lambda: send_username())
send_username_button.pack(side=LEFT, padx=10)

perfil_buttom = ttk.Button(username_frame, state=DISABLED, text="Perfil", style="primary.TButton",width=6, command=lambda: show_perfil())
perfil_buttom.pack(side=RIGHT, padx=10)

# Frame para a pergunta
question_frame = ttk.Frame(app)
question_frame.pack(side="top", anchor="nw", pady=10, padx=10, fill=X)

ttk.Label(question_frame, text="Sua pergunta:", font=("Arial", 12)).pack(side=LEFT, padx=5)
question_entry = ttk.Entry(question_frame, width=40, font=("Arial", 12))
question_entry.pack(side=LEFT, fill=X, expand=TRUE, padx=5)
send_question_button = ttk.Button(question_frame, text="Enviar Pergunta", width=20, state=DISABLED, style="primary.TButton", command=lambda: threading.Thread(target=send_question).start())
send_question_button.pack(side=LEFT, padx=10)

# Área de resposta
response_frame = ttk.Frame(app)
response_frame.pack(side="top", anchor="nw",pady=10, padx=10, fill=X)

response_text = ttk.Text(response_frame, height=6, width=80, font=("Arial", 12))  # Aumentando a largura para 80
response_text.pack(padx=5)

# Frame centralizado para elementos abaixo da resposta
central_frame = ttk.Frame(app)
central_frame.pack(pady=10, padx=10, anchor=CENTER)

# Frame para a adivinhação
guess_frame = ttk.Frame(central_frame)
guess_frame.pack(pady=10)

ttk.Label(guess_frame, text="Acha que foi Humano ou IA?", font=("Arial", 12)).pack(side=LEFT, padx=5)
guess_combobox = ttk.Combobox(guess_frame, values=["humano", "ia"], font=("Arial", 12), state="readonly")
guess_combobox.pack(side=LEFT, padx=5)
send_response_button = ttk.Button(guess_frame, text="Enviar Resposta", style="primary.TButton", state=DISABLED, command=lambda: threading.Thread(target=send_response).start())
send_response_button.pack(side=LEFT, padx=10)

# Status e contadores
status_frame = ttk.Frame(central_frame)
status_frame.pack(pady=10)

status_label = ttk.Label(status_frame, text="", font=("Arial", 12))
status_label.pack()

counts_frame = ttk.Frame(central_frame)
counts_frame.pack(pady=10)

ia_count_label = ttk.Label(counts_frame, text="Respostas de IA: 0", font=("Arial", 12))
ia_count_label.pack(side=LEFT, padx=10)
human_count_label = ttk.Label(counts_frame, text="Respostas de Humanos: 0", font=("Arial", 12))
human_count_label.pack(side=LEFT, padx=10)
correct_guesses_label = ttk.Label(counts_frame, text="Acertos: 0", font=("Arial", 12))
correct_guesses_label.pack(side=LEFT, padx=10)

# Botões para nova pergunta e encerrar
action_frame = ttk.Frame(central_frame)
action_frame.pack(pady=10)

new_question_button = ttk.Button(action_frame, state=NORMAL, text="Nova Pergunta", style="primary.TButton", command=lambda: clear_question())
new_question_button.pack(side=LEFT, padx=10)
close_button = ttk.Button(action_frame, text="Encerrar", style="danger.TButton", command=lambda: close_client())
close_button.pack(side=LEFT, padx=10)

# Área que irá definir os frames do perfil
data_frame = ttk.Frame(perfil_frame)
data_frame.pack(side="top", anchor="nw",pady=10, padx=10)

#passar o historico aqui
data_text = ttk.Text(data_frame, height=20, width=83, font=("Arial", 12))  # Aumentando a largura para 80
data_text.pack(padx=5)

historico_text = ttk.Text(data_text, height=20, width=83, font=("Arial", 12))  # Aumentando a largura para 80
historico_text.pack(padx=5)

quantidade_de_perguntas = ttk.Label(data_frame, text=f"Quantidade de perguntas: {quantidade_de_perguntas_dados}", font=("Arial", 12))
quantidade_de_perguntas.pack(side=LEFT, padx=10)
respostas_corretas = ttk.Label(data_frame, text=f"Acertos: {respostas_corretas_dados}", font=("Arial", 12))
respostas_corretas.pack(side=LEFT, padx=10)
precisao = ttk.Label(data_frame, text=f"Precisão: {precisao_dados}%", font=("Arial", 12))
precisao.pack(side=LEFT, padx=10)

# Botão para voltar à tela principal
voltar_button = ttk.Button(perfil_frame, text="Voltar", command=lambda: voltar())
voltar_button.pack(pady=20, side="top", anchor="nw")

# Funções de comunicação com o servidor
def send_username():
    global s

    if not username.get():
        status_label.config(text="Por favor, insira um nome de usuário.")
        return
    
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((HOST, PORT))
        s.send(username.get().encode())

        send_question_button.configure(state=NORMAL)
        perfil_buttom.configure(state=NORMAL)
        send_username_button.configure(state=DISABLED)

        status_label.config(text="Nome enviado. Agora, você pode enviar perguntas.")
    except socket.error as sock_err:
        status_label.config(text=f"Erro de socket: {sock_err}")
        clear_question()
    except Exception as error:
        status_label.config(text=f"Erro ao conectar ao servidor: {error}")
        clear_question()

def send_question():
    send_question_button.configure(state=DISABLED)

    global s
    if not s:
        status_label.config(text="Não há conexão com o servidor. Envie o nome primeiro.")
        return

    texto = question_entry.get().strip()
    if not texto:
        status_label.config(text="Nenhuma pergunta fornecida. Tente novamente.")
        return
    
    try:
        s.send(texto.encode())
        data = s.recv(BUFFER_SIZE)
        texto_recebido = data.decode('utf-8')
        response_text.delete("1.0", END)
        response_text.insert(END, texto_recebido)

        send_response_button.configure(state=NORMAL)
    except socket.error as sock_err:
        status_label.config(text=f"Erro de socket: {sock_err}")
        clear_question()

def send_response():
    send_response_button.configure(state=DISABLED)

    global s, total_ia, total_human, correct_guesses

    if not s:
        status_label.config(text="Não há conexão com o servidor. Envie o nome primeiro.")
        return

    origem = guess_combobox.get().strip().lower()
    if not origem:
        status_label.config(text="Selecione 'humano' ou 'IA'.")
        return

    try:
        s.send(origem.encode())
        feedback = s.recv(BUFFER_SIZE).decode('utf-8')
        status_label.config(text=feedback)

        if origem == "ia":
            total_ia += 1
        elif origem == "humano":
            total_human += 1

        if feedback.lower().strip() == "correto!":
            correct_guesses += 1

        update_labels()
    except socket.error as sock_err:
        status_label.config(text=f"Erro de socket: {sock_err}")
        clear_question()

# Função para mostrar a tela de perfil
def show_perfil():
    global quantidade_de_perguntas_dados
    global respostas_corretas_dados
    global precisao_dados

    consulta_cliente.consulta_documento(username.get())
    quantidade_de_perguntas_dados = consulta_cliente.retorna_quantidade_perguntas()
    respostas_corretas_dados = consulta_cliente.retorna_quantidade_acertos()
    precisao_dados = consulta_cliente.retorna_precisao()
    historico = consulta_cliente.retorna_user_log()

    # Atualizando o texto do Label para refletir a nova quantidade de perguntas
    quantidade_de_perguntas.config(text=f"Quantidade de perguntas: {quantidade_de_perguntas_dados}")

    respostas_corretas.config(text=f"Acertos: {respostas_corretas_dados}")

    precisao.config(text=f"Precisão: {precisao_dados:.2f}%")

    historico_text.delete("1.0", END)
    historico_text.insert(END, historico)

    # Esconde o frame principal e mostra o frame de perfil
    username_frame.pack_forget()
    question_frame.pack_forget()
    response_frame.pack_forget()
    central_frame.pack_forget()
    guess_frame.pack_forget()
    status_frame.pack_forget()
    counts_frame.pack_forget()
    action_frame.pack_forget()
    perfil_frame.pack(fill=X, expand=True)

# Função para voltar para a tela principal
def voltar():
    # Esconde o frame de perfil e mostra o frame principal
    perfil_frame.pack_forget()

    # Mostra novamente todos os frames da tela principal
    username_frame.pack(side="top", anchor="nw", padx=10, pady=10, fill=X)
    question_frame.pack(side="top", anchor="nw", pady=10, padx=10, fill=X)
    response_frame.pack(side="top", anchor="nw", pady=10, padx=10, fill=X)
    central_frame.pack(pady=10, padx=10, anchor=CENTER)
    guess_frame.pack(side="top", anchor="nw", pady=10, padx=10, fill=X)
    status_frame.pack(side="top", anchor="nw", pady=10, padx=10, fill=X)
    counts_frame.pack(side="top", anchor="nw", pady=10, padx=10, fill=X)
    action_frame.pack(side="top", anchor="nw", pady=10, padx=10, fill=X)

def clear_question():
    username_entry.delete(0, END)
    question_entry.delete(0, END)
    response_text.delete("1.0", END)

    send_username_button.configure(state=NORMAL)
    send_question_button.configure(state=DISABLED)
    send_response_button.configure(state=DISABLED)
    perfil_buttom.configure(state=DISABLED)

def close_client():
    if s:
        s.close()
    app.quit()

def update_labels():
    """Função para atualizar os rótulos de contagem."""
    ia_count_label.config(text=f"Respostas de IA: {total_ia}")
    human_count_label.config(text=f"Respostas de Humanos: {total_human}")
    correct_guesses_label.config(text=f"Acertos: {correct_guesses}")

if __name__ == "__main__":
    app.mainloop()