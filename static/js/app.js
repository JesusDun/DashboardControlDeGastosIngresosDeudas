// Archivo: static/js/app.js
var app = angular.module('myApp', []);

// --- Controlador de Login (Sin cambios) ---
app.controller("loginCtrl", function ($scope, $http) {
    $("#frmLogin").on("submit", function (event) {
        event.preventDefault();
        $.post("/iniciarSesion", $(this).serialize())
            .done(function () { 
                // NUEVO: Redirige al dashboard
                window.location.href = '/dashboard'; 
            })
            .fail(function (response) { alert(response.responseJSON.error || "Error al iniciar sesión."); });
    });
}); //

// --- Controlador de Registro (Sin cambios) ---
app.controller("registroCtrl", function ($scope, $http) {
    $("#frmRegistro").on("submit", function(event) {
        event.preventDefault();
        $.post("/registrarUsuario", $(this).serialize())
            .done(function(response) {
                alert(response.status);
                window.location.href = '/'; // Redirige al login
            })
            .fail(function(response) {
                alert(response.responseJSON.error || "Error en el registro.");
            });
    });
}); //


// =========================================================================
// --- ¡NUEVO! Controlador para el Dashboard ---
// =========================================================================
app.controller("dashboardCtrl", function ($scope, $http) {

    // --- Instancias de Gráficos ---
    let chartInstances = {};

    // --- Lógica de Saludo (Reutilizada) ---
    function actualizarSaludo() {
        const horaActual = new Date().getHours(); 
        let saludo = "";
        if (5 <= horaActual && horaActual < 12) { saludo = "Buenos Días"; }
        else if (12 <= horaActual && horaActual < 20) { saludo = "Buenas Tardes"; }
        else { saludo = "Buenas Noches"; }
        $("#saludo-texto").text(saludo);
    }
    
    // --- Lógica de Filtros ---
    function inicializarFiltros() {
        const ahora = new Date();
        const mesActual = ahora.getMonth() + 1; // getMonth() es 0-11
        const anoActual = ahora.getFullYear();
        
        // Asignar valores por defecto a los <select>
        $("#filtroMes").val(mesActual);
        $("#filtroAno").val(anoActual);
    }

    // --- Función Principal de Carga de Datos ---
    function buscarYActualizarTodo() {
        // Obtenemos los valores de los filtros
        const mes = $("#filtroMes").val();
        const ano = $("#filtroAno").val();

        // 1. Cargar la tabla de gastos recientes
        $.get(`/api/fin/tbodyGastos`, function (html) { 
            $("#tbodyGastos").html(html); 
        });
        
        // 2. Cargar todos los datos del dashboard (KPIs y Gráficos)
        $.get(`/api/fin/dashboard_data?mes=${mes}&ano=${ano}`, function (data) {
            actualizarKPIs(data.kpi);
            actualizarGraficos(data.charts);
        }).fail(function(err) {
            console.error("Error al cargar datos del dashboard:", err);
            alert("Error al cargar datos del dashboard.");
        });
    }

    // --- Funciones de Actualización de UI ---
    
    function actualizarKPIs(kpi) {
        const formatCurrency = (val) => `$${val.toFixed(2)}`;
        
        $("#kpiTotalIngresado").text(formatCurrency(kpi.total_ingresado));
        $("#kpiTotalGastado").text(formatCurrency(kpi.total_gastado));
        $("#kpiBalanceNeto").text(formatCurrency(kpi.balance_neto));
        
        // Cambiar color del balance
        const balanceCard = $("#cardBalanceNeto");
        if (kpi.balance_neto > 0) {
            balanceCard.removeClass('bg-danger').addClass('bg-success');
        } else if (kpi.balance_neto < 0) {
            balanceCard.removeClass('bg-success').addClass('bg-danger');
        } else {
            balanceCard.removeClass('bg-success bg-danger').addClass('bg-secondary');
        }
        
        $("#kpiDeudasPagadas").text(kpi.deudas_pagadas);
        $("#kpiDeudasPendientes").text(kpi.deudas_pendientes);
        $("#kpiTotalPendiente").text(formatCurrency(kpi.total_pendiente));
    }

    function actualizarGraficos(charts) {
        // 1. Gastos por Categoría (Pie)
        const catData = {
            labels: charts.gastos_categoria.map(c => c.categoria),
            values: charts.gastos_categoria.map(c => c.total)
        };
        dibujarGrafico('chartGastosCategoria', 'pie', catData, "Gastos por Categoría");

        // 2. Gastos por Método de Pago (Dona)
        const metodoData = {
            labels: charts.gastos_metodo_pago.map(m => m.metodo_pago),
            values: charts.gastos_metodo_pago.map(m => m.total)
        };
        dibujarGrafico('chartMetodoPago', 'doughnut', metodoData, "Métodos de Pago");

        // 3. Deudas por Estado (Pie)
        const estadoData = {
            labels: charts.deudas_por_estado.map(d => d.estado),
            values: charts.deudas_por_estado.map(d => d.total)
        };
        dibujarGrafico('chartDeudasEstado', 'pie', estadoData, "Deudas por Estado");

        // 4. Saldo Pendiente por Deudor (Barra)
        const deudorData = {
            labels: charts.deudas_por_deudor.map(d => d.deudor),
            values: charts.deudas_por_deudor.map(d => d.pendiente)
        };
        dibujarGrafico('chartDeudasDeudor', 'bar', deudorData, "Saldo Pendiente por Deudor");
    }

    // --- Función Genérica para Dibujar Gráficos ---
    function dibujarGrafico(canvasId, tipo, data, etiqueta) {
        if (chartInstances[canvasId]) {
            chartInstances[canvasId].destroy(); // Destruir gráfico anterior
        }
        
        const ctx = document.getElementById(canvasId).getContext('2d');
        
        // Colores base (puedes personalizarlos más)
        const backgroundColors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', 
            '#DDA0DD', '#98D8C8', '#f7a072', '#a18cd1', '#fbc2eb'
        ];

        chartInstances[canvasId] = new Chart(ctx, {
            type: tipo,
            data: {
                labels: data.labels,
                datasets: [{
                    label: etiqueta,
                    data: data.values,
                    backgroundColor: backgroundColors.slice(0, data.labels.length)
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: (tipo === 'bar' ? 'none' : 'top'),
                    }
                },
                scales: (tipo === 'bar') ? { y: { beginAtZero: true } } : {}
            }
        });
    }


    // --- Eventos de Formularios (jQuery) ---
    
    // 1. Agregar Gasto
    $("#frmGasto").on("submit", function (event) {
        event.preventDefault();
        $.post("/api/fin/gasto", $(this).serialize())
            .done(() => { 
                this.reset(); 
                // No es necesario llamar a buscarYActualizarTodo() aquí,
                // Pusher se encargará de ello.
            })
            .fail((err) => alert("Error al agregar gasto: " + err.responseJSON.error));
    });

    // 2. Agregar Ingreso
    $("#frmIngreso").on("submit", function (event) {
        event.preventDefault();
        $.post("/api/fin/ingreso", $(this).serialize())
            .done(() => { 
                this.reset(); 
                // Ocultar modal si se está usando
                $('#modalIngreso').modal('hide'); 
            })
            .fail((err) => alert("Error al agregar ingreso: " + err.responseJSON.error));
    });

    // 3. Agregar Deuda
    $("#frmDeuda").on("submit", function (event) {
        event.preventDefault();
        $.post("/api/fin/deuda", $(this).serialize())
            .done(() => { 
                this.reset(); 
                $('#modalDeuda').modal('hide');
            })
            .fail((err) => alert("Error al agregar deuda: " + err.responseJSON.error));
    });
    
    // 4. Eliminar Gasto (desde la tabla)
    $(document).on("click", ".btn-eliminar-gasto", function () {
        const id = $(this).data("id");
        if (confirm(`¿Estás seguro de eliminar el gasto #${id}?`)) { 
            $.post("/api/fin/gasto/eliminar", { id: id })
                .fail((err) => alert("Error al eliminar: " + err.responseJSON.error));
        }
    });

    // 5. Botón de Cerrar Sesión
    $(document).on("click", "#btnCerrarSesion", function() {
        if (confirm("¿Estás seguro de que quieres cerrar sesión?")) {
            $.post("/cerrarSesion").done(function() {
                window.location.href = '/'; 
            });
        }
    }); //
    
    // 6. Botón de aplicar filtros
    $(document).on("click", "#btnAplicarFiltros", function() {
        console.log("Aplicando filtros...");
        buscarYActualizarTodo(); // Recarga todos los datos con los filtros seleccionados
    });


    // --- Lógica de Pusher (Actualizada) ---
    const pusher = new Pusher('b338714caa5dd2af623d', { cluster: 'us2' });
    // NUEVO: Canal de finanzas
    const channel = pusher.subscribe('canal-finanzas'); 
    channel.bind('evento-actualizacion', function(data) {
        console.log("¡Actualización de finanzas recibida!", data.message);
        // Recarga todo el dashboard para reflejar el cambio
        buscarYActualizarTodo(); 
    });
    
    // --- Carga Inicial ---
    actualizarSaludo();
    inicializarFiltros();
    buscarYActualizarTodo(); // Carga inicial de datos
});
