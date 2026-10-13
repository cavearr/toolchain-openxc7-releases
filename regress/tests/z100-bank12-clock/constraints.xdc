# clk on AB27, IO_L11P_T1_SRCC_12 of xc7z100ffg900: a P clock pad of bank
# 12. led on AA13, any free pad. Same dialect as the generated constraints.
set_property PACKAGE_PIN AB27 [get_ports clk]
set_property IOSTANDARD LVCMOS33 [get_ports clk]
set_property PACKAGE_PIN AA13 [get_ports led]
set_property IOSTANDARD LVCMOS33 [get_ports led]
