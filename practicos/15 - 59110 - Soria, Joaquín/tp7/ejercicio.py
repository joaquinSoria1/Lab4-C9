import streamlit as st
import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import matplotlib.pyplot as plt

# Configuración de la página
st.set_page_config(page_title="Predicción de Ventas", layout="wide")
st.title('Predicción de Ventas Diarias')
st.markdown("""
Esta aplicación permite explorar el efecto de diferentes parámetros en una red neuronal
para la predicción de ventas diarias. Ajuste los parámetros en el panel izquierdo y
presione 'Entrenar' para ver los resultados.
""")

# Panel lateral para parámetros
with st.sidebar:
    st.header("Parámetros de la Red Neuronal")
    
    learning_rate = st.slider(
        "Tasa de aprendizaje",
        min_value=0.0,
        max_value=1.0,
        value=0.01,  # Cambiado a 0.01 para mejor aprendizaje
        step=0.001,  # Paso más fino para mejor control
        help="Controla qué tanto se ajustan los pesos en cada iteración"
    )
    
    epochs = st.slider(
        "Cantidad de épocas",
        min_value=10,
        max_value=10000,
        value=1000,
        step=10,
        help="Número de veces que la red neuronal procesará todo el conjunto de datos"
    )
    
    hidden_neurons = st.slider(
        "Neuronas en capa oculta",
        min_value=1,
        max_value=100,
        value=10,  # Aumentado a 10 para mejor capacidad de aprendizaje
        step=1,
        help="Cantidad de neuronas en la capa oculta de la red"
    )

# Leer y preparar datos
@st.cache_data
def load_data():
    try:
        df = pd.read_csv('ventas.csv')
        if not all(col in df.columns for col in ['dia', 'ventas']):
            st.error("El archivo no contiene las columnas requeridas: 'dia' y 'ventas'")
            return None
        return df
    except Exception as e:
        st.error(f"Error al cargar el archivo: {str(e)}")
        return None

df = load_data()

if df is not None:
    # Normalizar datos
    X = torch.FloatTensor(df['dia'].values.reshape(-1, 1))
    y = torch.FloatTensor(df['ventas'].values.reshape(-1, 1))
    X_norm = (X - X.min()) / (X.max() - X.min())
    y_norm = (y - y.min()) / (y.max() - y.min())

    # Definir la red neuronal con arquitectura mejorada
    class SalesNetwork(nn.Module):
        def __init__(self, input_size, hidden_size, output_size):
            super(SalesNetwork, self).__init__()
            self.hidden1 = nn.Linear(input_size, hidden_size)
            self.hidden2 = nn.Linear(hidden_size, hidden_size)  # Segunda capa oculta
            self.output = nn.Linear(hidden_size, output_size)
            self.relu = nn.ReLU()
            self.dropout = nn.Dropout(0.1)  # Añadido dropout para regularización
            
        def forward(self, x):
            x = self.relu(self.hidden1(x))
            x = self.dropout(x)
            x = self.relu(self.hidden2(x))
            x = self.dropout(x)
            x = self.output(x)
            return x

    # Función de entrenamiento
    def train_network():
        torch.manual_seed(42)  # Para reproducibilidad
        model = SalesNetwork(1, hidden_neurons, 1)
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
        
        loss_values = []
        
        progress_container = st.empty()
        status_text = st.empty()
        
        with progress_container:
            progress_bar = st.progress(0)
        
        try:
            for epoch in range(epochs):
                model.train()  # Modo entrenamiento
                optimizer.zero_grad()
                
                outputs = model(X_norm)
                loss = criterion(outputs, y_norm)
                
                loss.backward()
                optimizer.step()
                
                loss_values.append(loss.item())
                
                if epoch % 10 == 0:  # Actualizar la barra cada 10 épocas
                    progress = (epoch + 1) / epochs
                    progress_bar.progress(progress)
                    status_text.text(f'Entrenando: Época {epoch+1}/{epochs}')
            
            status_text.empty()
            st.success('¡Entrenamiento completado exitosamente! 🎉')
            
            return model, loss_values
        except Exception as e:
            st.error(f"Error durante el entrenamiento: {str(e)}")
            return None, None

    # Graficar resultados
    def plot_results(model, loss_values):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Predicción de Ventas")
            fig_pred, ax_pred = plt.subplots(figsize=(10, 6))
            
            # Generar predicciones para una secuencia continua de días
            model.eval()  # Modo evaluación
            with torch.no_grad():
                x_continuo = torch.linspace(0, 1, 100).reshape(-1, 1)
                y_pred_continuo = model(x_continuo)
                # Desnormalizar predicciones
                x_continuo = x_continuo * (X.max() - X.min()) + X.min()
                y_pred_continuo = y_pred_continuo * (y.max() - y.min()) + y.min()
            
            ax_pred.scatter(df['dia'], df['ventas'], color='blue', label='Datos reales', alpha=0.5)
            ax_pred.plot(x_continuo, y_pred_continuo, color='red', label='Predicción', linewidth=2)
            ax_pred.set_xlabel('Día del mes')
            ax_pred.set_ylabel('Ventas')
            ax_pred.grid(True, linestyle='--', alpha=0.7)
            ax_pred.legend()
            st.pyplot(fig_pred)
        
        with col2:
            st.subheader("Evolución del Error")
            fig_loss, ax_loss = plt.subplots(figsize=(10, 6))
            ax_loss.plot(loss_values, color='green')
            ax_loss.set_xlabel('Época')
            ax_loss.set_ylabel('Error (MSE)')
            ax_loss.grid(True, linestyle='--', alpha=0.7)
            ax_loss.set_yscale('log')  # Escala logarítmica para mejor visualización
            st.pyplot(fig_loss)

    # Inicializar placeholder para los gráficos
    if 'show_graphs' not in st.session_state:
        st.session_state.show_graphs = False

    # Botón de entrenamiento
    if st.sidebar.button('Entrenar', type='primary'):
        model, loss_values = train_network()
        if model is not None:
            st.session_state.show_graphs = True
            plot_results(model, loss_values)
    
    # Mostrar datos originales solo si no se han mostrado los resultados del entrenamiento
    if not st.session_state.show_graphs:
        st.subheader("Datos de Ventas Originales")
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter(df['dia'], df['ventas'], color='blue', label='Datos reales', alpha=0.5)
        ax.set_xlabel('Día del mes')
        ax.set_ylabel('Ventas')
        ax.grid(True, linestyle='--', alpha=0.7)
        ax.legend()
        st.pyplot(fig)

else:
    st.warning("Por favor, asegúrese de que el archivo 'ventas.csv' esté disponible y tenga el formato correcto.")