################################################################################
# MRS Version: 2.3.0
# Automatically-generated file. Do not edit!
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../lib/driver/src/nor25_flash.c \
../lib/driver/src/printf.c 

C_DEPS += \
./lib/driver/src/nor25_flash.d \
./lib/driver/src/printf.d 

OBJS += \
./lib/driver/src/nor25_flash.o \
./lib/driver/src/printf.o 

DIR_OBJS += \
./lib/driver/src/*.o \

DIR_DEPS += \
./lib/driver/src/*.d \

DIR_EXPANDS += \
./lib/driver/src/*.253r.expand \


# Each subdirectory must supply rules for building sources it contributes
lib/driver/src/%.o: ../lib/driver/src/%.c
	@	riscv-wch-elf-gcc -march=rv32im -mabi=ilp32 -msmall-data-limit=8 -mno-save-restore -fmax-errors=20 -O3 -fmessage-length=0 -ffunction-sections -fdata-sections -g -I"d:/PDS/SparrowRV-master/bsp/bsp_app/app" -I"d:/PDS/SparrowRV-master/bsp/bsp_app/lib" -I"d:/PDS/SparrowRV-master/bsp/bsp_app/lib/perip/include" -I"d:/PDS/SparrowRV-master/bsp/bsp_app/lib/driver/include" -I"d:/PDS/SparrowRV-master/bsp/bsp_app/example/coremark" -std=gnu99 -MMD -MP -MF"$(@:%.o=%.d)" -MT"$(@)" -c -o "$@" "$<"

