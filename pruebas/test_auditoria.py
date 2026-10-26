"""La auditoría debe detectar corrupción, no solo aceptar la corrida original."""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from validar import validar


class AuditoriaTest(unittest.TestCase):
    def fixture(self):
        temp=tempfile.TemporaryDirectory()
        dest=Path(temp.name)
        for p in (ROOT/"salida/principal").iterdir():
            if p.is_file() and p.name!="validacion.json":
                (dest/p.name).symlink_to(p)
        return temp,dest

    def mutate_csv(self,dest,name,column,value):
        path=dest/name
        with path.open() as f:
            reader=csv.DictReader(f)
            cols=reader.fieldnames
            rows=list(reader)
        path.unlink()  # Solo enlace temporal: el original permanece intacto.
        rows[0][column]=value
        with path.open("w") as f:
            writer=csv.DictWriter(f,fieldnames=cols)
            writer.writeheader();writer.writerows(rows)

    def test_acepta_corrida_observada(self):
        temp,dest=self.fixture()
        with temp:
            self.assertEqual(validar(dest,principal=True)["errores"],0)

    def test_rechaza_unidad_creada(self):
        temp,dest=self.fixture()
        with temp:
            self.mutate_csv(dest,"hospitales.csv","stock_final","999")
            self.assertGreater(validar(dest)["errores"],0)

    def test_rechaza_respuesta_inventada(self):
        temp,dest=self.fixture()
        with temp:
            self.mutate_csv(dest,"accidentes.csv","respuesta_total_s","99999")
            self.assertGreater(validar(dest)["errores"],0)

    def test_rechaza_choque_sin_evidencia(self):
        temp,dest=self.fixture()
        with temp:
            self.mutate_csv(dest,"accidentes.csv","bus","vehiculo_inexistente")
            self.assertGreater(validar(dest)["errores"],0)

    def test_negativa_total_reintenta_sin_perder_flota(self):
        folder=ROOT/"salida/denegacion_total"
        with (folder/"accidentes.csv").open() as f:
            accidents=list(csv.DictReader(f))
        with (folder/"hospitales.csv").open() as f:
            hospitals=list(csv.DictReader(f))
        self.assertGreater(len(accidents),0)
        self.assertTrue(all(r["estado"]=="espera" and not r["unidad"] and not r["respuesta_total_s"] for r in accidents))
        self.assertEqual(sum(int(r["stock_inicial"]) for r in hospitals),sum(int(r["stock_final"]) for r in hospitals))
        events=[json.loads(line) for line in (folder/"eventos.jsonl").read_text().splitlines()]
        for a in accidents:
            attempts=[e["t"] for e in events if e["evento"]=="SIN_AMBULANCIA" and e["detalle"].startswith(a["id"]+" ")]
            self.assertGreater(len(attempts),1)
            self.assertTrue(all(b-a==30 for a,b in zip(attempts,attempts[1:])))


if __name__=="__main__":
    unittest.main()
