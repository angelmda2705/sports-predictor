export function MockBanner() {
  return (
    <div
      role="status"
      className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 dark:border-amber-700/60 dark:bg-amber-900/20 dark:text-amber-200"
    >
      <strong>Datos de demostración.</strong> Esta vista contiene{" "}
      <em>datos de prueba (mock)</em> claramente etiquetados: equipos, calendario y
      marcadores <strong>no son reales</strong>. Sirven para desarrollo mientras se
      conectan los proveedores de datos autorizados.
    </div>
  );
}
