import streamlit as st
import requests
import datetime
import calendar
import threading

st.set_page_config(page_title="Vacaciones Operarios", page_icon="📅", layout="centered")

# Reemplaza con tu URL pública de Apps Script
API_URL = "https://script.google.com/macros/s/AKfycbxs3HejJqWfWpEls3s1N7mciFAuWO4eEi2xMVA-18HWogzSjlW7730kW07CI0hKljoU_g/exec"

EQUIPOS_BASE = ["Equipo Edgar", "Equipo Chuy", "Equipo Cristian", "Equipo Martín", "Personal de Apoyo"]

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "usuario" not in st.session_state:
    st.session_state.usuario = {}
if "dias_seleccionados" not in st.session_state:
    st.session_state.dias_seleccionados = []
if "mostrar_aviso_rh" not in st.session_state:
    st.session_state.mostrar_aviso_rh = False

def request_api_async(payload):
    def worker():
        try:
            requests.post(API_URL, json=payload, allow_redirects=True)
        except:
            pass
    threading.Thread(target=worker, daemon=True).start()

def request_api_sync(payload):
    try:
        res = requests.post(API_URL, json=payload, allow_redirects=True)
        return res.json()
    except:
        return {"status": "error"}

@st.cache_data(ttl=2)
def fetch_data():
    try:
        response = requests.get(f"{API_URL}?action=getData")
        return response.json()
    except:
        return {"personal": [], "diasOcupados": []}

@st.dialog("📌 Recordatorio Importante")
def aviso_rh_pop_up():
    st.warning("Recuerda recoger tu pase de vacaciones y entregarlo a RH al menos un día hábil antes de tu día de vacaciones.")
    if st.button("Entendido", use_container_width=True, type="primary"):
        st.session_state.mostrar_aviso_rh = False
        st.rerun()

# --- INTERFAZ DE LOGIN ---
if not st.session_state.logged_in:
    st.markdown("<h2 style='text-align: center;'>🔒 Acceso de Personal</h2>", unsafe_allow_html=True)
    
    with st.form("login_form"):
        nombre_input = st.text_input("Nombre(s)", placeholder="Ej. Edgar").strip()
        apellido_input = st.text_input("Apellido(s)", placeholder="Ej. Martinez").strip()
        nomina_input = st.text_input("Número de Nómina", placeholder="Ej. 56").strip()
        
        if st.form_submit_button("Ingresar", use_container_width=True):
            if nombre_input.lower() == "admin" and apellido_input.lower() == "admin" and nomina_input == "448":
                st.session_state.logged_in = True
                st.session_state.usuario = {"nombre": "Admin", "nomina": "448", "equipo": "Ninguno", "rol": "Admin"}
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
                    st.error("Datos incorrectos. Verifica tu Nombre, Apellido y Nómina.")

# --- INTERFAZ POST-LOGIN ---
else:
    user = st.session_state.usuario
    meses_es = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
    hoy = datetime.date.today()
    fecha_limite_solicitud = hoy + datetime.timedelta(days=7)
    
    # ---------------- ROL: ADMINISTRADOR ----------------
    if user["rol"] == "Admin":
        st.title("🛡️ Panel de Administrador")
        
        data = fetch_data()
        equipos_unicos = sorted(list(set(EQUIPOS_BASE + [p[3] for p in data["personal"] if p[4] != "Admin"])))
        
        tab1, tab2, tab3 = st.tabs(["👥 Gestor de Equipos", "👤 Alta / Baja", "📅 Gestión de Vacaciones"])
        
        # TAB 1: GESTOR DE EQUIPOS
        with tab1:
            st.subheader("1. Cambiar de equipo a un operario")
            lista_operarios = [f"{p[1]} {p[2]} ({p[0]})" for p in data["personal"] if p[4] != "Admin"]
            if lista_operarios:
                op_seleccionado = st.selectbox("Selecciona al operario:", lista_operarios)
                nuevo_equipo = st.selectbox("Asignar a nuevo equipo:", equipos_unicos)
                
                if st.button("Guardar Cambio de Equipo", use_container_width=True):
                    id_nomina = op_seleccionado.split("(")[-1].replace(")", "")
                    res = request_api_sync({"action": "actualizarEquipo", "nomina": id_nomina, "nuevoEquipo": nuevo_equipo})
                    
                    if res.get("status") == "success":
                        if res.get("conflictos", 0) > 0:
                            st.warning(f"⚠️ Equipo actualizado. Se detectaron {res['conflictos']} conflicto(s) de fecha. Se ha enviado una alerta por correo a los encargados.")
                        else:
                            st.success("✅ Equipo actualizado correctamente. Todas sus fechas se transfirieron a su nuevo equipo.")
                        fetch_data.clear()
                        st.rerun()
            
            st.divider()
            st.subheader("2. Renombrar un equipo completo")
            equipo_a_renombrar = st.selectbox("Selecciona el equipo a renombrar:", equipos_unicos)
            nuevo_nombre_equipo = st.text_input("Nuevo nombre para el equipo:").strip()
            if st.button("Renombrar Equipo", use_container_width=True):
                if nuevo_nombre_equipo:
                    request_api_sync({"action": "renombrarEquipo", "equipoAntiguo": equipo_a_renombrar, "equipoNuevo": nuevo_nombre_equipo})
                    fetch_data.clear()
                    st.success("Equipo renombrado con éxito.")
                    st.rerun()

            st.divider()
            st.subheader("3. Mantenimiento Retroactivo de la Base de Datos")
            st.caption("Usa este botón para corregir solicitudes históricas pasadas/futuras de personas que cambiaron de equipo antes de las actualizaciones recientes.")
            if st.button("🔄 Reparar e Igualar Historial Completo", use_container_width=True, type="primary"):
                with st.spinner("Procesando reestructuración retroactiva en Google Sheets y Calendario..."):
                    res_rep = request_api_sync({"action": "repararHistorialMaestro"})
                    if res_rep.get("status") == "success":
                        fetch_data.clear()
                        if res_rep.get("empalmes", 0) > 0:
                            st.warning(f"⚠️ Historial reparado. Se detectaron {res_rep['empalmes']} empalmes históricos. Se envió un reporte detallado a tu correo.")
                        else:
                            st.success("🎉 Historial reparado con éxito. Se actualizaron todas las solicitudes pasadas y futuras.")
                        st.rerun()

        # TAB 2: ALTA / BAJA DE PERSONAL
        with tab2:
            st.subheader("Agregar nuevo trabajador")
            with st.form("form_alta"):
                nuevo_nom = st.text_input("Nombre(s)").strip()
                nuevo_ape = st.text_input("Apellido(s)").strip()
                nueva_num_nom = st.text_input("Número de Nómina").strip()
                equipo_destino = st.selectbox("Asignar a equipo:", equipos_unicos)
                if st.form_submit_button("➕ Registrar en Plantilla", use_container_width=True):
                    if nuevo_nom and nueva_num_nom:
                        request_api_sync({"action": "agregarPersonal", "nombre": nuevo_nom, "apellido": nuevo_ape, "nomina": nueva_num_nom, "equipo": equipo_destino})
                        fetch_data.clear()
                        st.success("Trabajador registrado.")
                        st.rerun()
            
            st.divider()
            st.subheader("Dar de baja a un trabajador")
            if lista_operarios:
                op_baja = st.selectbox("Selecciona al integrante:", lista_operarios, key="baja")
                if st.button("🗑️ Eliminar Trabajador", use_container_width=True):
                    request_api_sync({"action": "eliminarPersonal", "nomina": op_baja.split("(")[-1].replace(")", "")})
                    fetch_data.clear()
                    st.success("Trabajador eliminado.")
                    st.rerun()

        # TAB 3: GESTIÓN DE VACACIONES
        with tab3:
            st.subheader("Gestión de Vacaciones por Persona")
            
            lista_operarios_gest = [f"{p[1]} {p[2]} (Nómina: {p[0]})" for p in data["personal"] if p[4] != "Admin"]
            
            if lista_operarios_gest:
                op_sel_gest = st.selectbox("Selecciona al operario a consultar/modificar:", lista_operarios_gest)
                id_nomina_sel = op_sel_gest.split("(Nómina: ")[-1].replace(")", "").strip()
                usuario_gest = next((p for p in data["personal"] if str(p[0]) == id_nomina_sel), None)
                
                if usuario_gest:
                    st.success(f"Operario: {usuario_gest[1]} {usuario_gest[2]} | Equipo Actual: {usuario_gest[3]}")
                    
                    if "admin_mes" not in st.session_state:
                        st.session_state.admin_mes = hoy.month
                        st.session_state.admin_anio = hoy.year
                    
                    c1, c2, c3 = st.columns([1, 2, 1])
                    if c1.button("⬅️ Ant.", key="adm_ant"):
                        st.session_state.admin_mes = 12 if st.session_state.admin_mes == 1 else st.session_state.admin_mes - 1
                        st.session_state.admin_anio -= 1 if st.session_state.admin_mes == 12 else 0
                        st.rerun()
                    
                    c2.markdown(f"<h4 style='text-align: center;'>{meses_es[st.session_state.admin_mes]} {st.session_state.admin_anio}</h4>", unsafe_allow_html=True)
                    
                    if c3.button("Sig. ➡️", key="adm_sig"):
                        st.session_state.admin_mes = 1 if st.session_state.admin_mes == 12 else st.session_state.admin_mes + 1
                        st.session_state.admin_anio += 1 if st.session_state.admin_mes == 1 else 0
                        st.rerun()
                    
                    fechas_usuario = [str(d[0]).split("T")[0] for d in data["diasOcupados"] if str(d[2]) == str(usuario_gest[0])]
                    
                    cal = calendar.Calendar(firstweekday=6)
                    mes_dias = cal.monthdatescalendar(st.session_state.admin_anio, st.session_state.admin_mes)
                    
                    st.write("Presiona un día apartado (🟡) para **CANCELARLO**.")
                    cols_dias = st.columns(7)
                    for i, d_sem in enumerate(["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]):
                        cols_dias[i].markdown(f"<p style='text-align:center; font-weight:bold; margin:0;'>{d_sem}</p>", unsafe_allow_html=True)
                    
                    for semana in mes_dias:
                        cols = st.columns(7)
                        for idx, dia in enumerate(semana):
                            with cols[idx]:
                                if dia.month != st.session_state.admin_mes:
                                    st.write("")
                                else:
                                    dia_str = dia.strftime("%Y-%m-%d")
                                    if dia_str in fechas_usuario:
                                        if st.button(f"🟡 {dia.day}", key=f"del_{dia_str}", use_container_width=True):
                                            res = request_api_sync({
                                                "action": "cancelarDiaEspecifico", 
                                                "nomina": str(usuario_gest[0]), 
                                                "nombre": f"{usuario_gest[1]} {usuario_gest[2]}", 
                                                "equipo": usuario_gest[3],
                                                "fecha": dia_str
                                            })
                                            if res.get("status") == "success":
                                                fetch_data.clear()
                                                st.success(f"Día {dia_str} cancelado y liberado con éxito.")
                                                st.rerun()
                                    else:
                                        st.markdown(f"<button style='width:100%; border:none; padding:5px;' disabled>{dia.day}</button>", unsafe_allow_html=True)

        st.divider()
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

    # ---------------- ROL: OPERARIO (MÓVIL) ----------------
    else:
        if st.session_state.mostrar_aviso_rh:
            aviso_rh_pop_up()

        st.markdown(f"### 👋 ¡Hola, {user['nombre']}!")
        st.markdown(f"**Equipo:** {user['equipo']} | **Nómina:** {user['nomina']}")
        st.write("---")
        
        # Banner informativo de regla de 7 días
        fecha_limite_fmt = fecha_limite_solicitud.strftime("%d/%m/%Y")
        st.info(f"📌 **Regla de Anticipación:** Las vacaciones deben solicitarse con al menos **1 semana (7 días) de anticipación** (solicitudes permitidas a partir del **{fecha_limite_fmt}**).")
        
        data = fetch_data()
        fechas_bloqueadas = [str(d[0]).split("T")[0] for d in data["diasOcupados"] if d[1] == user["equipo"]]
        
        if "mes_actual" not in st.session_state:
            st.session_state.mes_actual = hoy.month
            st.session_state.anio_actual = hoy.year

        col_ant, col_mes, col_sig = st.columns([1, 2, 1])
        with col_ant:
            if st.button("⬅️ Ant.", use_container_width=True):
                st.session_state.mes_actual = 12 if st.session_state.mes_actual == 1 else st.session_state.mes_actual - 1
                st.session_state.anio_actual -= 1 if st.session_state.mes_actual == 12 else 0
                st.rerun()
        with col_mes:
            st.markdown(f"<h4 style='text-align: center; margin:0;'>📅 {meses_es[st.session_state.mes_actual]} {st.session_state.anio_actual}</h4>", unsafe_allow_html=True)
        with col_sig:
            if st.button("Sig. ➡️", use_container_width=True):
                st.session_state.mes_actual = 1 if st.session_state.mes_actual == 12 else st.session_state.mes_actual + 1
                st.session_state.anio_actual += 1 if st.session_state.mes_actual == 1 else 0
                st.rerun()

        st.write("Los días en **rojo🔴** ya están ocupados por tu equipo. Los días deshabilitados no cumplen con la anticipación de 7 días.")
        
        cal = calendar.Calendar(firstweekday=6)
        mes_dias = cal.monthdatescalendar(st.session_state.anio_actual, st.session_state.anio_actual if False else st.session_state.mes_actual)
        
        cols_dias = st.columns(7)
        for i, d_sem in enumerate(["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]):
            cols_dias[i].markdown(f"<p style='text-align:center; font-weight:bold; margin:0;'>{d_sem}</p>", unsafe_allow_html=True)

        # Filtrar fechas que ya no cumplan con la regla de 7 días en la selección guardada
        st.session_state.dias_seleccionados = [
            f for f in st.session_state.dias_seleccionados 
            if datetime.datetime.strptime(f, "%Y-%m-%d").date() >= fecha_limite_solicitud
        ]

        for semana in mes_dias:
            cols = st.columns(7)
            for idx, dia in enumerate(semana):
                with cols[idx]:
                    if dia.month != st.session_state.mes_actual:
                        st.write("") 
                    else:
                        dia_str = dia.strftime("%Y-%m-%d")
                        # 1. Regla de anticipación de 7 días (bloqueo automático si dia < fecha_limite_solicitud)
                        if dia < fecha_limite_solicitud:
                            st.markdown(f"<button style='width:100%; border:none; border-radius:5px; padding:5px; color:#aaa; background-color:#f0f0f0;' disabled>{dia.day}</button>", unsafe_allow_html=True)
                        # 2. Regla de un solo operario por equipo
                        elif dia_str in fechas_bloqueadas:
                            st.markdown(f"<button style='width:100%; background-color:#FF4B4B; color:white; border:none; border-radius:5px; padding:5px;' disabled>🔴 {dia.day}</button>", unsafe_allow_html=True)
                        # 3. Días disponibles para selección
                        else:
                            if dia_str in st.session_state.dias_seleccionados:
                                if st.button(f"✅ {dia.day}", key=f"btn_{dia_str}", use_container_width=True):
                                    st.session_state.dias_seleccionados.remove(dia_str)
                                    st.rerun()
                            else:
                                if st.button(str(dia.day), key=f"btn_{dia_str}", use_container_width=True):
                                    st.session_state.dias_seleccionados.append(dia_str)
                                    st.rerun()
        
        st.write("")
        if st.session_state.dias_seleccionados:
            resumen_dias = [f"{d.split('-')[2]}/{meses_es[int(d.split('-')[1])][:3]}" for d in sorted(st.session_state.dias_seleccionados)]
            st.info(f"Días marcados acumulados: {', '.join(resumen_dias)}")
            
            @st.dialog("Confirmar Solicitud")
            def confirmar_pop_up():
                st.write("Estás a punto de solicitar las siguientes fechas:")
                for f in sorted(st.session_state.dias_seleccionados):
                    p = f.split("-")
                    st.write(f"• {p[2]} de {meses_es[int(p[1])]} de {p[0]}")
                
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
                        request_api_async(payload)
                        fetch_data.clear()
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
