import streamlit as st
import requests
import datetime
import calendar

# Configuración de página optimizada para celular
st.set_page_config(page_title="Vacaciones Operarios", page_icon="📅", layout="centered")

# Reemplaza con la URL que copiaste al implementar tu Apps Script
API_URL = "https://script.google.com/macros/s/AKfycbxs3HejJqWfWpEls3s1N7mciFAuWO4eEi2xMVA-18HWogzSjlW7730kW07CI0hKljoU_g/exec"

# Inicializar estados de la sesión
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "usuario" not in st.session_state:
    st.session_state.usuario = {}
if "dias_seleccionados" not in st.session_state:
    st.session_state.dias_seleccionados = []

def fetch_data():
    try:
        response = requests.get(f"{API_URL}?action=getData")
        return response.json()
    except:
        st.error("Error al conectar con la base de datos de Google Sheets.")
        return {"personal": [], "diasOcupados": []}

# --- INTERFAZ DE LOGIN ---
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>🔒 Acceso de Personal</h2>", unsafe_allow_html=True)
    st.write("Ingresa tus datos para acceder al sistema:")
    
    nombre_input = st.text_input("Nombre(s)", placeholder="Ej. Edgar").strip()
    apellido_input = st.text_input("Apellido(s)", placeholder="Ej. Martinez").strip()
    nomina_input = st.text_input("Número de Nómina", placeholder="Ej. 56").strip()
    
    if st.button("Ingresar", use_container_width=True):
        if nombre_input.lower() == "admin" and apellido_input.lower() == "admin" and nomina_input == "448":
            st.session_state.logged_in = True
            st.session_state.usuario = {"nombre": "Admin", "nomina": 448, "equipo": "Ninguno", "rol": "Admin"}
            st.rerun()
        else:
            data = fetch_data()
            usuario_encontrado = None
            for p in data["personal"]:
                # p[0]=Nomina, p[1]=Nombre, p[2]=Apellido, p[3]=Equipo, p[4]=Rol
                if str(p[0]) == nomina_input and p[1].lower() == nombre_input.lower() and p[2].lower() == apellido_input.lower():
                    usuario_encontrado = {"nomina": p[0], "nombre": f"{p[1]} {p[2]}", "equipo": p[3], "rol": p[4]}
                    break
            
            if usuario_encontrado:
                st.session_state.logged_in = True
                st.session_state.usuario = usuario_encontrado
                st.rerun()
            else:
                st.error("Datos incorrectos. Por favor verifica tu Nombre, Apellido y Nómina.")

# --- INTERFAZ POST-LOGIN ---
else:
    user = st.session_state.usuario
    
    # ---------------- ROL: ADMINISTRADOR ----------------
    if user["rol"] == "Admin":
        st.title("🛡️ Panel de Administrador")
        st.write(f"Bienvenido, {user['nombre']}.")
        
        data = fetch_data()
        
        tab1, tab2 = st.tabs(["👥 Mover Equipos", "🔄 Restaurar Días"])
        
        with tab1:
            st.subheader("Cambiar integrante de equipo")
            lista_operarios = [f"{p[1]} {p[2]} ({p[0]})" for p in data["personal"] if p[4] != "Admin"]
            op_seleccionado = st.selectbox("Selecciona al operario:", lista_operarios)
            
            nuevo_equipo = st.selectbox("Asignar a nuevo equipo:", [
                "Equipo Edgar", "Equipo Chuy", "Equipo Cristian", "Equipo Martín", "Personal de Apoyo"
            ])
            
            if st.button("Guardar Cambio de Equipo", use_container_width=True):
                id_nomina = op_seleccionado.split("(")[-1].replace(")", "")
                res = requests.post(API_URL, json={"action": "actualizarEquipo", "nomina": id_nomina, "nuevoEquipo": nuevo_equipo})
                if res.status_code == 200:
                    st.success("Equipo actualizado con éxito en Google Sheets.")
                    st.rerun()
                    
        with tab2:
            st.subheader("Restaurar / Limpiar Vacaciones de un Operario")
            op_limpiar = st.selectbox("Selecciona al operario para liberar sus días:", lista_operarios, key="limpiar")
            if st.button("Liberar Días y Poner Disponibles", use_container_width=True):
                id_nomina = op_limpiar.split("(")[-1].replace(")", "")
                res = requests.post(API_URL, json={"action": "liberarDias", "nomina": id_nomina})
                if res.status_code == 200:
                    st.success("Días restaurados y puestos disponibles automáticamente.")
                    st.rerun()
                    
        if st.button("Cerrar Sesión", key="logout_admin", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    # ---------------- ROL: OPERARIO (MÓVIL) ----------------
    else:
        st.markdown(f"### 👋 ¡Hola, {user['nombre']}!")
        st.markdown(f"**Equipo:** {user['equipo']} | **Nómina:** {user['nomina']}")
        st.write("---")
        
        # Obtener datos frescos de ocupación
        data = fetch_data()
        
        # Filtrar fechas ocupadas SOLO para el equipo de este operario
        # Formato esperado en Sheets: "YYYY-MM-DD"
        fechas_bloqueadas = []
        for d in data["diasOcupados"]:
            # d[0]=Fecha, d[1]=Equipo, d[2]=Nomina
            if d[1] == user["equipo"]:
                # Normalizar formato de fecha de Google Sheets
                fecha_str = str(d[0]).split("T")[0]
                fechas_bloqueadas.append(fecha_str)
        
        # Calendario dinámico en tiempo real (Mes actual)
        hoy = datetime.date.today()
        st.markdown(f"#### 📅 Calendario de Vacaciones - **{calendar.month_name[hoy.month]} {hoy.year}**")
        st.write("Los días en **rojo🔴** ya están ocupados por compañeros de tu equipo.")
        
        cal = calendar.Calendar(firstweekday=6)
        mes_dias = cal.monthdatescalendar(hoy.year, hoy.month)
        
        # Renderizar cuadrícula visual interactiva emulando calendario móvil
        for semana in mes_dias:
            cols = st.columns(7)
            for idx, dia in enumerate(semana):
                with cols[idx]:
                    if dia.month != hoy.month:
                        st.write("") # Días fuera del mes actual vacíos
                    else:
                        dia_str = dia.strftime("%Y-%m-%d")
                        es_ocupado = dia_str in fechas_bloqueadas
                        
                        # Generar identificador de botón
                        label = f"{dia.day}"
                        
                        if es_ocupado:
                            st.markdown(f"<button style='width:100%; background-color:#FF4B4B; color:white; border:none; border-radius:5px; padding:5px; font-weight:bold;' disabled>🔴 {label}</button>", unsafe_allow_html=True)
                        else:
                            ya_seleccionado = dia_str in st.session_state.dias_seleccionados
                            if ya_seleccionado:
                                if st.button(f"✅ {label}", key=f"btn_{dia_str}", use_container_width=True):
                                    st.session_state.dias_seleccionados.remove(dia_str)
                                    st.rerun()
                            else:
                                if st.button(label, key=f"btn_{dia_str}", use_container_width=True):
                                    st.session_state.dias_seleccionados.append(dia_str)
                                    st.rerun()
        
        st.write("")
        if st.session_state.dias_seleccionados:
            st.info(f"Días marcados: {', '.join([d.split('-')[-1] for d in st.session_state.dias_seleccionados])}")
            
            # Botón Finalizar que activa la ventana pop-up (dialog nativo de Streamlit)
            @st.dialog("Confirmar Solicitud")
            def confirmar_pop_up():
                st.write(f"Estás a punto de solicitar las siguientes fechas de vacaciones:")
                for f in st.session_state.dias_seleccionados:
                    partes = f.split("-")
                    st.write(f"• {partes[2]} de {calendar.month_name[int(partes[1])]} de {partes[0]}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Confirmar", use_container_width=True, type="primary"):
                        # Enviar payload al backend de Google Apps Script
                        payload = {
                            "action": "solicitarVacaciones",
                            "nombre": user["nombre"],
                            "nomina": user["nomina"],
                            "equipo": user["equipo"],
                            "fechas": st.session_state.dias_seleccionados
                        }
                        res = requests.post(API_URL, json=payload)
                        if res.status_code == 200:
                            st.success("¡Solicitud de vacaciones enviada con éxito a los encargados del área!")
                            st.session_state.dias_seleccionados = []
                            st.toast("Notificación enviada por correo 📧")
                            st.rerun()
                with col2:
                    if st.button("Volver", use_container_width=True):
                        st.rerun()
            
            if st.button("Finalizar", use_container_width=True, type="primary"):
                confirmar_pop_up()
        
        if st.button("Salir / Cerrar Sesión", key="logout_op", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.dias_seleccionados = []
            st.rerun()