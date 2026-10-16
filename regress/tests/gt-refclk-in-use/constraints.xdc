# xc7a100tfgg484, GTP quad 216 (tile GTP_COMMON_X130Y179). The reference clock
# pair is MGTREFCLK0 (F6/E6), which the database gives to IBUFDS_GTE2_X0Y2, the
# lower buffer (Y0) of the tile, hardwired to GTREFCLK0 of GTPE2_COMMON_X0Y1.
# The clock and the LED are in bank 16.
set_property -dict { PACKAGE_PIN D17 IOSTANDARD LVCMOS33 } [get_ports {clk}]
set_property -dict { PACKAGE_PIN A13 IOSTANDARD LVCMOS33 } [get_ports {led}]
set_property PACKAGE_PIN F6 [get_ports {refclk_p}]
set_property PACKAGE_PIN E6 [get_ports {refclk_n}]
