
odoo.define('portal_stock_check.show_text', function (require) {
    'use strict';

    // Usar jQuery para la manipulación de la vista
    var $ = require('jquery');

    // Función que crea un gráfico (por ejemplo, gráfico de barras)
    function createBarChart(containerId, labels, data) {
        var ctx = document.getElementById(containerId).getContext('2d');
        if (!ctx) return;

        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Example Data',
                    data: data,
                    backgroundColor: ['#5fd6d6ff', '#9966ff', '#ffce56', '#ff1a4bff'],
                    borderColor: ['#ffffff', '#ffffff', '#ffffff', '#ffffff'],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom'
                    },
                    title: { display: false }
                }
            }
        });
    }

    // Exponer la función para usarla en otras partes
    return {
        createBarChart: createBarChart
    };
});
