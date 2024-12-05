import tkinter as tk
from tkinter import ttk, messagebox
from ultralytics import YOLO
import cv2
from collections import defaultdict
import os
import pandas as pd
from datetime import datetime
from PIL import Image, ImageTk
import mysql.connector

# Inicializar o modelo YOLO
model = YOLO("C:/Users/Iguzz/Documents/Codes/best.pt")

# Dicionário com os preços unitários de cada tipo de objeto
precos_unitarios = {
    'cremedeleite': 6.0,
    'bauduccowafertriplochocolate': 5.00,
    'colgate': 20.00,
    'guarana': 4.00,
    # Adicione mais classes e preços conforme necessário
}

# Variável para armazenar o total geral
total_geral = 0.0
data_list = []  # Lista de produtos detectados

# Captura da câmera (única instância)
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

# Função para conectar ao MySQL
def conectar_mysql():
    try:
        conn = mysql.connector.connect(
            host='127.0.0.1',
            user='root',  # Seu usuário do MySQL
            password='123698745',  # Sua senha do MySQL
            database='TCC'  # Nome do banco de dados
        )
        return conn
    except mysql.connector.Error as err:
        print(f"Erro ao conectar ao MySQL: {err}")
        return None

# Função para salvar dados no banco de dados MySQL
def salvar_dados_mysql(data_list):
    conn = conectar_mysql()
    if conn:
        cursor = conn.cursor()
        for item in data_list:
            # Verifica se o produto já existe no banco
            cursor.execute("SELECT * FROM compras WHERE PRODUTO = %s", (item['PRODUTO'],))
            result = cursor.fetchone()

            if result:
                # Atualiza a quantidade e total se o produto já existir
                cursor.execute("""
                    UPDATE compras
                    SET QUANTIDADE = QUANTIDADE + %s,
                        CUSTO_UNITARIO = %s
                    WHERE PRODUTO = %s
                """, (item['QUANTIDADE'], item['CUSTO_UNITARIO'], item['PRODUTO']))
            else:
                # Insere um novo produto no banco de dados
                cursor.execute("""
                    INSERT INTO compras (PRODUTO, QUANTIDADE, CUSTO_UNITARIO)
                    VALUES (%s, %s, %s)
                """, (item['PRODUTO'], item['QUANTIDADE'], item['CUSTO_UNITARIO']))
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Dados salvos no banco de dados MySQL")

# Função para adicionar ou atualizar a quantidade de um produto
def atualizar_lista_produtos(treeview, label_total, class_name, count):
    global total_geral
    produto_existe = False

    # Verificar se o produto já está na lista
    for item in data_list:
        if item['PRODUTO'] == class_name:
            item['QUANTIDADE'] += count
            item['TOTAL'] = item['QUANTIDADE'] * item['CUSTO_UNITARIO']
            produto_existe = True
            break

    # Se o produto não existe na lista, adicionar uma nova entrada
    if not produto_existe:
        data_atual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        custo_unitario = precos_unitarios.get(class_name, 0.0)
        total = count * custo_unitario
        data_list.append({
            'PRODUTO': class_name,
            'QUANTIDADE': count,
            'DATA': data_atual,
            'CUSTO_UNITARIO': custo_unitario,
            'TOTAL': total
        })

    # Atualizar interface gráfica (Treeview)
    for i in treeview.get_children():
        treeview.delete(i)
    for item in data_list:
        treeview.insert("", "end", values=(item['PRODUTO'], item['QUANTIDADE'], item['CUSTO_UNITARIO'], item['TOTAL']))

    # Atualizar o total geral
    total_geral = sum(item['TOTAL'] for item in data_list)
    label_total.config(text=f"Total Geral: R$ {total_geral:.2f}")

    # Salvar no banco de dados MySQL
    salvar_dados_mysql(data_list)

# Função para detecção de produtos
def detectar_produtos(treeview, label_total, frame_atual):
    # A detecção de produtos só será feita na imagem capturada no momento
    if frame_atual is None:
        messagebox.showwarning("Erro", "Nenhuma imagem foi capturada da câmera!")
        return

    results = model.track(frame_atual, persist=True)

    for result in results:
        try:
            class_ids = result.boxes.cls.int().cpu().tolist()  # IDs das classes
            class_names = [model.names[class_id] for class_id in class_ids]  # Nomes das classes

            class_counts = defaultdict(int)
            for class_name in class_names:
                class_counts[class_name] += 1

            for class_name, count in class_counts.items():
                atualizar_lista_produtos(treeview, label_total, class_name, count)

        except Exception as e:
            print(f"Erro: {e}")
            pass

# Função para capturar e exibir o vídeo continuamente
def mostrar_video(label_video):
    def atualizar_frame():
        success, img = cap.read()
        if success:
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img_rgb)
            img_tk = ImageTk.PhotoImage(image=img_pil)

            label_video.img_tk = img_tk
            label_video.config(image=img_tk)

            # Retornar a imagem capturada para detecção futura
            label_video.frame_atual = img

        label_video.after(10, atualizar_frame)

    atualizar_frame()

# Função para liberar a câmera e encerrar a aplicação
def fechar_aplicacao(root):
    cap.release()  # Libera a câmera
    root.quit()    # Fecha a janela principal

# Função para abrir a janela de pagamento
def abrir_janela_pagamento(root):
    def verificar_senha():
        senha = entry_senha.get()
        if senha == "1234":  # Senha simulada
            messagebox.showinfo("Pagamento", f"Pagamento de R$ {total_geral:.2f} efetuado com sucesso!")
            janela_pagamento.destroy()
            fechar_aplicacao(root)  # Fecha o aplicativo ao realizar o pagamento com sucesso
        else:
            messagebox.showwarning("Erro", "Senha incorreta. Tente novamente.")

    janela_pagamento = tk.Toplevel()
    janela_pagamento.title("Pagamento")
    janela_pagamento.geometry("300x400")

    label_valor = tk.Label(janela_pagamento, text=f"Total a pagar: R$ {total_geral:.2f}", font=("Arial", 14))
    label_valor.pack(pady=20)

    label_senha = tk.Label(janela_pagamento, text="Digite sua senha de 4 dígitos:", font=("Arial", 12))
    label_senha.pack()

    entry_senha = tk.Entry(janela_pagamento, show="*", font=("Arial", 18), width=4, justify='center')
    entry_senha.pack(pady=10)

    # Botões de números de 0 a 9
    frame_numeros = tk.Frame(janela_pagamento)
    frame_numeros.pack()

    def inserir_numero(num):
        entry_senha.insert(tk.END, num)

    for i in range(3):
        for j in range(3):
            numero = i * 3 + j + 1
            btn_numero = tk.Button(frame_numeros, text=str(numero), font=("Arial", 16), width=4, command=lambda n=numero: inserir_numero(n))
            btn_numero.grid(row=i, column=j)

    btn_zero = tk.Button(frame_numeros, text="0", font=("Arial", 16), width=4, command=lambda: inserir_numero(0))
    btn_zero.grid(row=3, column=1)

    # Botão de confirmação de senha
    btn_confirmar = tk.Button(janela_pagamento, text="Confirmar", font=("Arial", 16), command=verificar_senha)
    btn_confirmar.pack(pady=20)

# Interface separada para a câmera
def criar_interface_camera():
    camera_window = tk.Toplevel()
    camera_window.title("Câmera")
    camera_window.geometry("640x480")

    label_video = tk.Label(camera_window)
    label_video.pack()

    # Iniciar o vídeo da câmera
    mostrar_video(label_video)

    # Retornar o widget da câmera para futuras capturas de imagens
    return label_video

# Interface gráfica principal (Mercado)
def criar_interface_principal():
    root = tk.Tk()
    root.title("Mercado Virtual")
    root.geometry("800x600")

    # Tabela de produtos detectados
    columns = ('PRODUTO', 'QUANTIDADE', 'CUSTO_UNITARIO', 'TOTAL')
    treeview = ttk.Treeview(root, columns=columns, show='headings')
    treeview.heading('PRODUTO', text='Produto')
    treeview.heading('QUANTIDADE', text='Quantidade')
    treeview.heading('CUSTO_UNITARIO', text='Valor Unitário')
    treeview.heading('TOTAL', text='Total')
    treeview.pack(fill='both', expand=True)

    # Label para mostrar o total geral
    label_total = tk.Label(root, text="Total Geral: R$ 0.00", font=("Arial", 14))
    label_total.pack(pady=10)

    # Criar interface da câmera uma vez e manter aberta
    camera_label = criar_interface_camera()

    # Botão para detectar produtos
    btn_detectar = tk.Button(root, text="Detectar Produtos", command=lambda: detectar_produtos(treeview, label_total, camera_label.frame_atual))
    btn_detectar.pack(pady=10)

    # Botão de pagamento
    btn_pagamento = tk.Button(root, text="Pagamento", command=lambda: abrir_janela_pagamento(root))
    btn_pagamento.pack(pady=10)

    # Rodar a interface principal
    root.mainloop()

if __name__ == "__main__":
    criar_interface_principal()
