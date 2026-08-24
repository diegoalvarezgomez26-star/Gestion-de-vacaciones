import streamlit as st
import requests
import datetime
import calendar

st.set_page_config(page_title="Vacaciones Operarios", page_icon="📅", layout="centered")

# URL de tu implementación de Apps Script
API_URL = "TU_URL_DE_APPS_SCRIPT_AQUI"

# Inicializar estados de la sesión
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "usuario" not in st.session_state:
    st.session_state.usuario = {}
if "dias_seleccionados" not in st.session_state:
    st.session_state.dias_seleccionados = []
if "mostrar_aviso_rh" not in st.session_state:
    st.session_state.mostrar_aviso_rh = False

def fetch_data():
    try:
        response = requests.get(f"{API_URL}?action=getData")
        return response.json()
    except:
        st.error("Error al conectar con la base de datos de Google Sheets.")
        return {"personal": [], "diasOcupados": []}

# --- POP-UP DE INFORMACIÓN DE RH ---
@st.dialog("📌 Recordatorio Importante")
def aviso_rh_pop_up():
    st.warning("Recuerda recoger tu pase de vacaciones y entregarlo a RH al menos un día hábil antes de tu día de vacaciones.")
    st.write("")
    if st.button("Entendido", use_container_width=True, type="primary"):
        st.session_state.mostrar_aviso_rh = False
        st.rerun()

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
        equipos_unicos = list(set([p[3] for p in data["personal"] if p[4] != "Admin"]))
        
        tab1, tab2, tab3 = st.tabs(["👥 Gestor de Equipos", "👤 Alta / Baja de Personal", "🔄 Restaurar Días"])
        
        # TAB 1: MOVER O RENOMBRAR EQUIPOS
        with tab1:
            st.subheader("1. Cambiar de equipo a un operario")
            lista_operarios = [f"{p[1]} {p[2]} ({p[0]})" for p in data["personal"] if p[4] != "Admin"]
            if lista_operarios:
                op_seleccionado = st.selectbox("Selecciona al operario:", lista_operarios, key="sel_mover")
                nuevo_equipo = st.selectbox("Asignar a nuevo equipo:", equipos_unicos, key="sel_neq")
                
                if st.button("Guardar Cambio de Equipo", use_container_width=True):
                    id_nomina = op_seleccionado.split("(")[-1].replace(")", "")
                    res = requests.post(API_URL, json={"action": "actualizarEquipo", "nomina": id_nomina, "nuevoEquipo": nuevo_equipo})
                    if res.status_code == 200:
                        st.success("Equipo actualizado con éxito.")
                        st.rerun()
            
            st.write("---")
            st.subheader("2. Renombrar un equipo completo")
            equipo_a_renombrar = st.selectbox("Selecciona el equipo a renombrar:", equipos_unicos, key="sel_ren")
            nuevo_nombre_equipo = st.text_input("Nuevo nombre para el equipo:", placeholder="Ej. Equipo Roberto").strip()
            
            if st.button("Renombrar Equipo", use_container_width=True):
                if nuevo_nombre_equipo:
                    res = requests.post(API_URL, json={"action": "renombrarEquipo", "equipoAntiguo": equipo_a_renombrar, "equipoNuevo": nuevo_nombre_equipo})
                    if res.status_code == 200:
                        st.success(f"Se cambió el nombre de '{equipo_a_renombrar}' a '{nuevo_nombre_equipo}'.")
                        st.rerun()
                else:
                    st.warning("Escribe el nuevo nombre del equipo.")

        # TAB 2: ALTA Y BAJA DE PERSONAL
        with tab2:
            st.subheader("1. Agregar nuevo trabajador")
            nuevo_nom = st.text_input("Nombre(s)", key="add_nom").strip()
            nuevo_ape = st.text_input("Apellido(s)", key="add_ape").strip()
            nueva_num_nom = st.text_input("Número de Nómina", key="add_num").strip()
            equipo_destino = st.selectbox("Asignar a equipo:", equipos_unicos, key="add_eq")
            
            if st.button("➕ Registrar en Plantilla", use_container_width=True, type="primary"):
                if nuevo_nom and nuevo_ape and nueva_num_nom:
                    res = requests.post(API_URL, json={
                        "action": "agregarPersonal",
                        "nombre": nuevo_nom,
                        "apellido": nuevo_ape,
                        "nomina": nueva_num_nom,
                        "equipo": equipo_destino
                    })
                    if res.status_code == 200:
                        st.success(f"Trabajador {nuevo_nom} {nuevo_ape} registrado con éxito.")
                        st.rerun()
                else:
                    st.warning("Completa todos los campos obligatorios.")
            
            st.write("---")
            st.subheader("2. Dar de baja a un trabajador")
            if lista_operarios:
                op_baja = st.selectbox("Selecciona al integrante a eliminar:", lista_operarios, key="sel_baja")
                if st.button("🗑️ Eliminar Trabajador", use_container_width=True):
                    id_nomina_baja = op_baja.split("(")[-1].replace(")", "")
                    res = requests.post(API_URL, json={"action": "eliminarPersonal", "nomina": id_nomina_baja})
                    if res.status_code == 200:
                        st.success("Trabajador eliminado de la plantilla.")
                        st.rerun()

        # TAB 3: RESTAURAR DÍAS
        with tab3:
            st.subheader("Restaurar / Limpiar Vacaciones de un Operario")
            if lista_operarios:
                op_limpiar = st.selectbox("Selecciona al operario para liberar sus días:", lista_operarios, key="limpiar")
                if st.button("Liberar Días y Poner Disponibles", use_container_width=True):
                    id_nomina = op_limpiar.split("(")[-1].replace(")", "")
                    res = requests.post(API_URL, json={"action": "liberarDias", "nomina": id_nomina})
                    if res.status_code == 200:
                        st.success("Días restaurados correctamente.")
                        st.rerun()

        if st.button("Cerrar Sesión", key="logout_admin", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    # ---------------- ROL: OPERARIO (MÓVIL) ----------------
    else:
        # Mostrar el pop-up de RH al ser activado tras enviar la solicitud
        if st.session_state.mostrar_aviso_rh:
            aviso_rh_pop_up()

        st.markdown(f"### 👋 ¡Hola, {user['nombre']}!")
        st.markdown(f"**Equipo:** {user['equipo']} | **Nómina:** {user['nomina']}")
        st.write("---")
        
        data = fetch_data()
        fechas_bloqueadas = [str(d[0]).split("T")[0] for d in data["diasOcupados"] if d[1] == user["equipo"]]
        
        hoy = datetime.date.today()
        if "mes_actual" not in st.session_state:
            st.session_state.mes_actual = hoy.month
        if "anio_actual" not in st.session_state:
            st.session_state.anio_actual = hoy.year

        meses_es = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
            7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
        }

        col_ant, col_mes, col_sig = st.columns([1, 2, 1])
        with col_ant:
            if st.button("⬅️ Ant.", use_container_width=True):
                if st.session_state.mes_actual == 1:
                    st.session_state.mes_actual = 12
                    st.session_state.anio_actual -= 1
                else:
                    st.session_state.mes_actual -= 1
                st.rerun()
                
        with col_mes:
            nombre_mes = meses_es[st.session_state.mes_actual]
            st.markdown(f"<h4 style='text-align: center; margin:0;'>📅 {nombre_mes} {st.session_state.anio_actual}</h4>", unsafe_allow_html=True)
            
        with col_sig:
            if st.button("Sig. ➡️", use_container_width=True):
                if st.session_state.mes_actual == 12:
                    st.session_state.mes_actual = 1
                    st.session_state.anio_actual += 1
                else:
                    st.session_state.mes_actual += 1
                st.rerun()

        st.write("Los días en **rojo🔴** ya están ocupados por compañeros de tu equipo.")
        
        cal = calendar.Calendar(firstweekday=6)
        mes_dias = cal.monthdatescalendar(st.session_state.anio_actual, st.session_state.mes_actual)
        
        dias_semana = ["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]
        cols_dias = st.columns(7)
        for i, d_sem in enumerate(dias_semana):
            cols_dias[i].markdown(f"<p style='text-align:center; font-weight:bold; margin:0;'>{d_sem}</p>", unsafe_allow_html=True)

        for semana in mes_dias:
            cols = st.columns(7)
            for idx, dia in enumerate(semana):
                with cols[idx]:
                    if dia.month != st.session_state.mes_actual:
                        st.write("") 
                    else:
                        dia_str = dia.strftime("%Y-%m-%d")
                        es_ocupado = dia_str in fechas_bloqueadas
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
            resumen_dias = [f"{d.split('-')[2]}/{meses_es[int(d.split('-')[1])][:3]}" for d in sorted(st.session_state.dias_seleccionados)]
            st.info(f"Días marcados acumulados: {', '.join(resumen_dias)}")
            
            @st.dialog("Confirmar Solicitud")
            def confirmar_pop_up():
                st.write("Estás a punto de solicitar las siguientes fechas de vacaciones:")
                for f in sorted(st.session_state.dias_seleccionados):
                    partes = f.split("-")
                    st.write(f"• {partes[2]} de {meses_es[int(partes[1])]} de {partes[0]}")
                
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Confirmar", use_container_width=True, type="primary"):
                        payload = {
                            "action": "solicitarVacaciones",
                            "nombre": user["nombre"],
                            "nomina": user["nomina"],
                            "equipo": user["equipo"],
                            "fechas": st.session_state.dias_seleccionados
                        }
                        res = requests.post(API_URL, json=payload)
                        if res.status_code == 200:
                            st.session_state.dias_seleccionados = []
                            st.session_state.mostrar_aviso_rh = True
                            st.rerun()
                with col2:
                    if st.button("Volver", use_container_width=True):
                        st.rerun()
            
            if st.button("Finalizar", use_container_width=True, type="primary"):
                confirmar_pop_up()
        
        if st.button("Salir / Cerrar Sesión", key="logout_op", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.dias_seleccionados = []
            st.session_state.mes_actual = hoy.month
            st.session_state.anio_actual = hoy.year
            st.rerun()
