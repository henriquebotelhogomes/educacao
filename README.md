# 🎓 Tutor Inteligente IA
Um sistema educacional avançado e interativo, construído com Inteligência Artificial para revolucionar a forma como educadores e estudantes interagem com o material de estudo.

## 📑 Índice
#### ✨ Funcionalidades
#### 🛠️ Tecnologias Utilizadas
#### ⚙️ Pré-requisitos
#### 🚀 Guia de Instalação
#### ⚠️ Notas para Windows

## ✨ Funcionalidades

O sistema está dividido em três secções principais, pensadas para otimizar o fluxo de aprendizagem:

### 1. 📝 Gerador de Exercícios

* Geração Automática: Criação de listas de exercícios de escolha múltipla adaptadas ao tema.

* Personalização Avançada: Ajuste por disciplina e nível de dificuldade.

* Exportação Simples: Descarregue o material diretamente para um ficheiro .docx (Microsoft Word).

### 2. 📚 Treinar Tutor (RAG)

* Upload em Lote: Carregamento de múltiplos ficheiros PDF em simultâneo.

* Processamento Inteligente (Docling): IA de visão avançada que mantém a estrutura visual, tabelas e o sentido semântico do texto original.

* Vector Store Cloud: Armazenamento vetorial seguro e rápido na nuvem através do Qdrant.

3. 🤖 Chat com Tutor

* Agente Conversacional: Um tutor interativo que compreende o contexto do aluno.

* Tool Calling Avançado: O agente consulta a base de dados vetorial autonomamente antes de formular uma resposta.

* Zero Alucinações: Respostas precisas baseadas exclusivamente no material de estudo fornecido pelo utilizador.

## 🛠️ Tecnologias Utilizadas

|**Componente**|**Tecnologia**|**Descrição**|
|------------|-----------|----------|
 |**Interface Gráfica**|Streamlit|Framework para criação rápida de web apps em Python.|
|**Orquestração IA**|LangChain|Gestão de Agentes, Tool Calling e Text Splitters.|
|**Cérebro (LLM)**|Llama-3.3-70b|Modelo open-source servido via Groq API para máxima velocidade.|
|**Embeddings**|HuggingFace|Modelo all-MiniLM-L6-v2 para vetorização local de texto.|
|**Base de Dados**|Qdrant Cloud|Armazenamento de vetores de alta performance em nuvem.|
|**Processamento**|Docling|Leitura estruturada e inteligente de PDFs complexos.|

## ⚙️ Pré-requisitos

Antes de iniciar, certifique-se de que tem os seguintes elementos preparados:

* Computador com Python 3.12 ou superior instalado.
* Chave de API do Groq (gratuita, para acesso ao modelo de linguagem).
* Conta e Chave de API do Qdrant Cloud (para o cluster vetorial).
* Ligação estável à internet para descarregar os modelos na primeira execução.

## 🚀 Guia de Instalação

Siga estes passos para colocar o projeto a correr na sua máquina local.

### Passo 1: Preparar o Ambiente

Crie e ative um ambiente virtual para isolar as dependências do projeto:
```
# Criar o ambiente virtual
python -m venv .venv

# Ativar no Windows:
.venv\Scripts\activate

# Ativar no Linux / macOS:
source .venv/bin/activate
```

### Passo 2: Instalar Dependências

Certifique-se de que possui o ficheiro requirements.txt atualizado e instale as bibliotecas:
```
pip install --no-cache-dir -r requirements.txt
```

### Passo 3: Configurar Credenciais

Crie um ficheiro oculto chamado .env na pasta raiz do projeto e adicione as suas chaves:
```
GROQ_API_KEY=sua_chave_groq_aqui
QDRANT_URL=sua_url_cluster_qdrant_aqui
QDRANT_API_KEY=sua_chave_qdrant_aqui
```

### Passo 4: Executar a Aplicação

Inicie o servidor local do Streamlit:
```
streamlit run app.py
```

## ⚠️ Notas para Windows (WinError 1314)

Se estiver a utilizar o sistema operativo Windows, este projeto já inclui uma correção nativa no ficheiro ```app.py``` para evitar o erro de falta de privilégios (```[WinError 1314]```).

A biblioteca Hugging Face tenta criar atalhos simbólicos (symlinks) por predefinição. O nosso código já desativa esse comportamento com as seguintes linhas (que não devem ser removidas):
```
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"
```

Desenvolvido para ferramenta de auxílio a educadores e estudantes.