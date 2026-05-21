################################################################################
# MRS Version: 2.3.0
# Automatically-generated file. Do not edit!
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../app/main.c \
../app/trap_handler.c 

C_DEPS += \
./app/main.d \
./app/trap_handler.d 

OBJS += \
./app/main.o \
./app/trap_handler.o 

DIR_OBJS += \
./app/*.o \

DIR_DEPS += \
./app/*.d \

DIR_EXPANDS += \
./app/*.253r.expand \


# Each subdirectory must supply rules for building sources it contributes
app/%.o: ../app/%.c
	@	riscv-wch-elf-gcc -march=rv32im -mabi=ilp32 -msmall-data-limit=8 -mno-save-restore -fmax-errors=20 -O3 -fmessage-length=0 -ffunction-sections -fdata-sections -g -I"d:/PDS/SparrowRV-master/bsp/bsp_app/app" -I"d:/PDS/SparrowRV-master/bsp/bsp_app/lib" -I"d:/PDS/SparrowRV-master/bsp/bsp_app/lib/perip/include" -I"d:/PDS/SparrowRV-master/bsp/bsp_app/lib/driver/include" -I"d:/PDS/SparrowRV-master/bsp/bsp_app/example/coremark" -std=gnu99 -MMD -MP -MF"$(@:%.o=%.d)" -MT"$(@)" -c -o "$@" "$<"

