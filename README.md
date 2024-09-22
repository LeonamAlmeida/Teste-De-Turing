# Tutorial de execução

# Banco de Dados
## Requerimentos para Instalação do BD

### Windows
Por favor, instale o **Pacote Redistribuível do Visual C++ 2015** (ou mais recente) antes de iniciar o servidor RavenDB.  
Esse pacote deve ser o único requisito para plataformas "Windows".  

### Linux
Recomendamos fortemente que você **atualize o sistema operacional Linux** antes de iniciar o servidor RavenDB.  
Além disso, verifique os pré-requisitos para o .NET no Linux.

### MacOS
Recomendamos fortemente que você **atualize o MacOS** e verifique os pré-requisitos para o .NET no macOS.

### Baixar o BD
- Baixe a última versão estável do RavenDB [aqui](https://ravendb.net/download) (6.2.0).
- Extraia o arquivo em uma pasta permanente para instalação e configuração do BD.
- Identifique e execute o arquivo `run` com o PowerShell.

### Configuração do BD
- Uma interface será aberta na web:
  - Aceitar os termos -> Next -> Unsecure -> Finish -> Restart Server.
- O banco de dados estará pronto para uso.

---

## Requerimentos para Uso do Programa

### Verificar Python e Pip
- Verifique se o Python e o Pip já estão instalados (use os comandos `python --version` e `pip --version`).
- Caso não estejam instalados, baixe-os e instale.

### Instalar Requerimentos do Projeto
- Baixe os requerimentos com o comando:
  ```bash
  pip install -r requirements.txt
## Execução do Projeto

1. Abra o banco de dados (caso já não esteja aberto), executando o arquivo `run` com PowerShell.
2. Na interface do RavenDB, vá na aba **Databases** e clique em **New database**.
   - Coloque como nome **BD2** e clique em **Quick create**.
3. Execute o servidor TCP por linha de comando no terminal com o comando abaixo(caso queira fechar o servidor, ‘mate’ o processo, fechando o terminal que está rodando o mesmo):
   ```bash
   python tcp_server.py
4. Execute o cliente TCP com o comando:
    ```bash
   python tcp_server.py
5. Pronto, o projeto está pronto para uso

OBS: Utilizamos a api do Rapidapi.com para obtermos a consulta do Gpt 4, como utilizamos a versão gratuita estamos limitados a 50 respostas automáticas mensais por key gerada.
