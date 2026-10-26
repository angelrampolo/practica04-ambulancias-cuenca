SHELL := /bin/bash
PYTHON ?= python3
SUMO := ./scripts/en_docker.sh

.PHONY: ayuda red demanda base principal extension estres repetir modos denegacion validar graficas informe pruebas reproducir gui gui-validar
ayuda:
	@echo 'make reproducir  — prepara, simula, compara, valida y genera el informe'
	@echo 'make base principal extension estres repetir modos validar graficas informe pruebas'
	@echo 'La red docente y el ZIP están archivados; SUMO usa van3twin:jammy.'
	@echo 'make gui — demostración interactiva; make gui-validar — capturas automáticas'
gui:
	./scripts/demo_gui.sh
gui-validar:
	./scripts/demo_gui.sh --automatico
red:
	$(SUMO) python3 scripts/preparar.py red
demanda:
	$(SUMO) python3 scripts/preparar.py demanda
base:
	$(SUMO) python3 scripts/linea_base.py
principal:
	mkdir -p salida/principal
	$(SUMO) bash -c 'python3 scripts/reto_ambulancias.py > salida/principal/ejecutor.log 2>&1'
extension:
	$(SUMO) python3 scripts/lote.py
estres:
	$(SUMO) python3 scripts/lote.py --semillas 42 --politicas cercano --tasa 15
repetir:
	$(SUMO) python3 scripts/lote.py --repeticion
	$(PYTHON) scripts/comprobar_repeticion.py
modos:
	$(SUMO) python3 scripts/experimento_modos.py
denegacion:
	mkdir -p salida/denegacion_total
	$(SUMO) bash -c 'python3 scripts/reto_ambulancias.py --p-sin 1 --end 1200 --output salida/denegacion_total > salida/denegacion_total/ejecutor.log 2>&1'
validar:
	$(PYTHON) scripts/validar.py --todos
graficas:
	$(PYTHON) scripts/analisis.py
informe:
	$(PYTHON) scripts/informe.py
pruebas:
	$(PYTHON) -m unittest discover -s pruebas -v
reproducir:
	$(MAKE) red
	$(MAKE) demanda
	$(MAKE) base
	$(MAKE) principal
	$(MAKE) extension
	$(MAKE) estres
	$(MAKE) repetir
	$(MAKE) modos
	$(MAKE) denegacion
	$(MAKE) gui-validar
	$(MAKE) validar
	$(MAKE) pruebas
	$(MAKE) graficas
	$(MAKE) informe
