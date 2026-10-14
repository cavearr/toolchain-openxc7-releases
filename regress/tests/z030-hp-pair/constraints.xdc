# Bank 33 is HP (RIOB18), all LVCMOS18. Tile A = RIOB18_X79Y67: a_in on M2
# (IO_L16P_T2_33, IOB_Y0), a_out on L2 (IO_L16N_T2_33, IOB_Y1). Tile B =
# RIOB18_X79Y65: b_out16 on N4 (IO_L17P_T2_33, IOB_Y0), M4 left unused.
# The clock and the capture flip-flop's output are in bank 12.
set_property -dict { PACKAGE_PIN AC13 IOSTANDARD LVCMOS18 } [get_ports {clk}]
set_property -dict { PACKAGE_PIN M2 IOSTANDARD LVCMOS18 } [get_ports {a_in}]
set_property -dict { PACKAGE_PIN L2 IOSTANDARD LVCMOS18 } [get_ports {a_out}]
set_property -dict { PACKAGE_PIN N4 DRIVE 16 IOSTANDARD LVCMOS18 } [get_ports {b_out16}]
set_property -dict { PACKAGE_PIN AC12 IOSTANDARD LVCMOS18 } [get_ports {cap}]
