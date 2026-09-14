#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
fc_test_binary=$(mktemp /tmp/fc-mpu-test.XXXXXX)
trap 'rm -f "$fc_test_binary"' EXIT
cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined \
  -Ifirmware/tests/stubs -Ifirmware/main \
  firmware/tests/test_mpu6500.c firmware/main/mpu6500.c -lm -o "$fc_test_binary"
"$fc_test_binary"
cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined \
  -Ifirmware/main firmware/tests/test_command.c firmware/main/fc_command.c \
  -o "$fc_test_binary"
"$fc_test_binary"
cc -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined \
  -Ifirmware/main firmware/tests/test_control.c firmware/main/fc_control.c \
  firmware/main/pid.c -lm -o "$fc_test_binary"
"$fc_test_binary"
