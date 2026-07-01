.PHONY: all proxy backend-check clean distclean

BUILD_DIR := build/proxy
PROXY_BIN := services/proxy/bin/P1gROXY
PYTHON ?= python3

all: proxy backend-check

proxy:
	cmake -S services/proxy -B $(BUILD_DIR) -DCMAKE_BUILD_TYPE=Release
	cmake --build $(BUILD_DIR) --parallel
	mkdir -p services/proxy/bin
	cp $(BUILD_DIR)/P1gROXY $(PROXY_BIN)

backend-check:
	$(PYTHON) -m py_compile \
		services/warehousehub/app/__init__.py \
		services/warehousehub/app/app.py \
		services/warehousehub/app/deflate_stream.py

clean:
	rm -rf $(BUILD_DIR) services/proxy/bin

distclean: clean
	rm -rf services/warehousehub/.venv var
