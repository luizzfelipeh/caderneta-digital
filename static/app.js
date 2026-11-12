// Caderneta Digital - pequenos comportamentos da interface
// (arquivo separado, sem JavaScript dentro do HTML, por causa da política de segurança CSP)
document.addEventListener("DOMContentLoaded", function () {
  // Pede confirmação antes de excluir lançamentos ou inativar cliente
  document.querySelectorAll("form[data-confirmar]").forEach(function (form) {
    form.addEventListener("submit", function (evento) {
      if (!window.confirm(form.dataset.confirmar)) {
        evento.preventDefault();
      }
    });
  });

  // Botão "Pagou tudo": preenche o valor com o saldo devedor
  document.querySelectorAll("[data-preencher-valor]").forEach(function (botao) {
    botao.addEventListener("click", function () {
      var campo = document.getElementById("valor");
      if (campo) {
        campo.value = botao.dataset.preencherValor;
        campo.focus();
      }
    });
  });
});
