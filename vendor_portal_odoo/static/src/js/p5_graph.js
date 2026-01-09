odoo.define('my_module.show_text', function (require) {
    'use strict';

    $(document).ready(function () {
        // Cambiar el texto dentro del <p> dinámicamente usando JS
        var dynamicText = document.getElementById('dynamic-text');
        dynamicText.innerHTML = 'Este es un texto dinámico actualizado con JavaScript!';
    });
});
