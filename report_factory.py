import json
import io
import csv
from abc import ABC, abstractmethod

class Reporte(ABC):
    def __init__(self, datos):
        self.datos = datos

    @abstractmethod
    def generar_reporte(self):
        pass
    
    @abstractmethod
    def get_mimetype(self):
        pass

    # --- ¡CORRECCIÓN AQUÍ! ---
    @abstractmethod # ANTES: @abstractbody
    def get_filename(self):
        pass
    # --- FIN DE LA CORRECCIÓN ---

class ReporteCSV(Reporte):
    def generar_reporte(self):
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(['ID', 'Descripcion', 'Monto', 'Categoria', 'Fecha', 'Metodo_Pago'])
        
        for gasto in self.datos:
            writer.writerow([
                gasto['id'], 
                gasto['descripcion'], 
                gasto['monto'], 
                gasto['categoria'], 
                gasto['fecha'],
                gasto.get('metodo_pago', '') 
            ])
        
        return output.getvalue()

    def get_mimetype(self):
        return 'text/csv'

    def get_filename(self):
        return 'gastos_financieros.csv'

class ReporteJSON(Reporte):
    def generar_reporte(self):
        return json.dumps(self.datos, indent=4) 

    def get_mimetype(self):
        return 'application/json'

    def get_filename(self):
        return 'gastos_financieros.json'

class ReportFactory:
    def crear_reporte(self, tipo, datos):
        if tipo == 'csv':
            return ReporteCSV(datos)
        elif tipo == 'json':
            return ReporteJSON(datos)
        else:
            raise ValueError("Tipo de reporte no válido")
