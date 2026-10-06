
function confirmarBorrado() {
    return confirm("¿Seguro? No se puede deshacer.");
}


document.addEventListener("DOMContentLoaded", function() {
    const form = document.getElementById("form-registro");
    if (form) {
        form.addEventListener("submit", function(e) {
            if (form.contraseña.value !== form.confirmar.value) {
                alert("Las contraseñas no son iguales");
                e.preventDefault();
            }
        });
    }
});