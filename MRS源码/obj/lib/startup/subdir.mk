################################################################################
# MRS Version: 2.3.0
# Automatically-generated file. Do not edit!
################################################################################

# Add inputs and outputs from these tool invocations to the build variables 
C_SRCS += \
../lib/startup/init.c 

C_DEPS += \
./lib/startup/init.d 

S_UPPER_SRCS += \
../lib/startup/startup.S 

S_UPPER_DEPS += \
./lib/startup/startup.d 

OBJS += \
./lib/startup/init.o \
./lib/startup/startup.o 

DIR_OBJS += \
./lib/startup/*.o \

DIR_DEPS += \
./lib/startup/*.d \

DIR_EXPANDS += \
./lib/startup/*.253r.expand \


# Each subdirectory must supply rules for building sources it contributes
lib/startup/%.o: ../lib/startup/%.c
	@	riscv-wch-elf-gcc -march=rv32im -mabi=ilp32 -msmall-data-limit=8 -mno-save-restore -fmax-errors=20 -O3 -fmessage-length=0 -ffunction-sections -fdata-sections -g -I"d:/PDS/SparrowRV-master/bsp/bsp_app/app" -I"d:/PDS/SparrowRV-master/bsp/bsp_app/lib" -I"d:/PDS/SparrowRV-master/bsp/bsp_app/lib/perip/include" -I"d:/PDS/SparrowRV-master/bsp/bsp_app/lib/driver/include" -I"d:/PDS/SparrowRV-master/bsp/bsp_app/example/coremark" -std=gnu99 -MMD -MP -MF"$(@:%.o=%.d)" -MT"$(@)" -c -o "$@" "$<"

lib/startup/%.o: ../lib/startup/%.S
	@	riscv-wch-elf-gcc -march=rv32im -mabi=ilp32 -msmall-data-limit=8 -mno-save-restore -fmax-errors=20 -O3 -fmessage-length=0 -ffunction-sections -fdata-sections -g -x assembler-with-cpp -I"d:/PDS/SparrowRV-master/bsp/bsp_app/lib/startup" -MMD -MP -MF"$(@:%.o=%.d)" -MT"$(@)" -c -o "$@" "$<"

