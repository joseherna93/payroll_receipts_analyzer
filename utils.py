import os
import re
import glob
import mysql.connector
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()

class SQLConnection:
    def __init__(self):
        """Inicializa la conexión a la base de datos utilizando variables de entorno."""
        self.host = os.getenv('MYSQL_HOST')
        self.user = os.getenv('MYSQL_USER')
        self.password = os.getenv('MYSQL_PASSWORD')
        self.database = os.getenv('MYSQL_DATABASE')
        self.connection = None
        self.connect()

    def connect(self):
        """Establece la conexión a la base de datos."""
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database
            )
            print("Conexión a MySQL establecida exitosamente.")
        except mysql.connector.Error as err:
            print(f"Error al conectar a MySQL: {err}")
            self.connection = None

    def close(self):
        """Cierra la conexión a la base de datos si está abierta."""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("Conexión a MySQL cerrada.")

    def execute_many(self, query, data):
        """Ejecuta una consulta SQL con múltiples conjuntos de datos."""
        if not self.connection or not self.connection.is_connected():
            print("No hay conexión activa a la base de datos.")
            return
        
        cursor = self.connection.cursor()
        try:
            cursor.executemany(query, data)
            self.connection.commit()
            print(f"{cursor.rowcount} filas insertadas.")
        except mysql.connector.Error as err:
            print(f"Error ejecutando la consulta: {err}")
        finally:
            cursor.close()

class PayrollProcessor:
    def __init__(self, xml_file):
        self.xml_file = xml_file
        self.ns = {
            'nomina12': 'http://www.sat.gob.mx/nomina12',
            'cfdi': None
        }
        self.data = {
            'emitter': set(),
            'receiver': set(),
            'payslip': set(),
            'movement_type': set(),
            'movements': set()
        }

    def extract_data(self):
        """Procesa el archivo XML y extrae los datos necesarios."""
        tree = ET.parse(self.xml_file)
        root = tree.getroot()
        self.ns['cfdi'] = root.tag.split('}')[0].strip('{}')

        # Obtener datos de la nómina
        payslip_id = re.search(r'[A-Fa-f0-9]{8}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{4}-[A-Fa-f0-9]{12}', self.xml_file).group(0)
        payroll = root.find('.//nomina12:Nomina', self.ns)
        final_payment_date = payroll.get('FechaFinalPago')
        initial_payment_date = payroll.get('FechaInicialPago')
        payment_date = payroll.get('FechaPago')
        payroll_type = payroll.get('TipoNomina')
        days_paid = payroll.get('NumDiasPagados')
        total_deductions = payroll.get('TotalDeducciones') or 0
        total_other_payments = payroll.get('TotalOtrosPagos') or 0
        total_perceptions = payroll.get('TotalPercepciones') or 0
        version = payroll.get('Version')

        # Obtener el elemento Emisor
        emitter = root.find('.//cfdi:Emisor', self.ns)
        emitter_id = emitter.get("Rfc")
        emitter_name = emitter.get('Nombre')
        emitter_fiscal_regime = emitter.get("RegimenFiscal")
        self.data['emitter'].add((emitter_id, emitter_name, emitter_fiscal_regime))

        # Obtener el elemento Receptor
        receiver = root.find('.//cfdi:Receptor', self.ns)
        receiver_id = receiver.get('Rfc')
        receiver_name = receiver.get('Nombre')
        receiver_cfdi_use = receiver.get('UsoCFDI')
        receiver_fiscal_address = receiver.get('DomicilioFiscalReceptor')
        receiver_fiscal_regime = receiver.get('RegimenFiscalReceptor')
        self.data['receiver'].add((receiver_id, receiver_name, receiver_cfdi_use, receiver_fiscal_address, receiver_fiscal_regime))
        
        # Agregar datos a payslip
        self.data['payslip'].add((
            payslip_id, emitter_id, receiver_id, initial_payment_date, 
            final_payment_date, payment_date, days_paid, payroll_type, 
            total_deductions, total_other_payments, total_perceptions, version
        ))

        # Procesar Percepciones y Deducciones
        self._process_movements(payroll, payslip_id, 'Percepcion', 'P')
        self._process_movements(payroll, payslip_id, 'Deduccion', 'D')

    def _process_movements(self, payroll, payslip_id, tag, trans_type):
        """Procesa movimientos dentro de percepciones o deducciones."""
        for movement in payroll.findall(f'.//nomina12:{tag}', self.ns):
            movement_type_id = movement.get('Clave')
            concept = movement.get('Concepto')
            exempt_amount = movement.get('ImporteExento') or 0
            taxable_amount = movement.get('ImporteGravado') or 0
            sub_type = movement.get('TipoPercepcion' if tag == 'Percepcion' else 'TipoDeduccion') or ''

            self.data['movement_type'].add((movement_type_id, concept, trans_type, sub_type))
            self.data['movements'].add((payslip_id, movement_type_id, exempt_amount, taxable_amount, 0))

class PayrollDataInserter:
    def __init__(self, db_connection):
        self.db_connection = db_connection

    def insert_data(self, data):
        """Inserta datos en las tablas correspondientes."""
        queries = {
            'emitter': """
                INSERT INTO emitter (id, name, fiscal_regime)
                VALUES (%s, %s, %s);
            """,
            'receiver': """
                INSERT INTO receiver (id, name, cfdi_use, fiscal_address, fiscal_regime)
                VALUES (%s, %s, %s, %s, %s);
            """,
            'payslip': """
                INSERT INTO payslip (
                    id, emitter_id, receiver_id, initial_payment_date, 
                    final_payment_date, payment_date, days_paid, type, 
                    total_deductions, total_other_payments, total_perceptions, version
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            """,
            'movement_type': """
                INSERT INTO movement_type (id, concept, transaction_type, transaction_sub_type)
                VALUES (%s, %s, %s, %s);
            """,
            'movements': """
                INSERT INTO movements (
                    payslip_id, movement_type_id, exempt_amount, taxable_amount, amount
                ) VALUES (%s, %s, %s, %s, %s);
            """
            
        }
        
        for key, values in data.items():
            if values:
                self.db_connection.execute_many(queries[key], list(values))