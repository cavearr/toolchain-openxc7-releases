# xc7a100tfgg484, GTP quad 216. The reference clock pair is MGTREFCLK0 (F6/E6),
# IBUFDS_GTE2_X0Y2, into GTREFCLK0 of GTPE2_COMMON_X0Y1. The channel takes the
# pads of lane 0 (TX B4/A4, RX B8/A8), which puts it on GTPE2_CHANNEL_X0Y4, a
# channel of the same quad. The clock and the LED are in bank 16.
set_property -dict { PACKAGE_PIN D17 IOSTANDARD LVCMOS33 } [get_ports {clk}]
set_property -dict { PACKAGE_PIN A13 IOSTANDARD LVCMOS33 } [get_ports {led}]
set_property PACKAGE_PIN F6 [get_ports {refclk_p}]
set_property PACKAGE_PIN E6 [get_ports {refclk_n}]
set_property PACKAGE_PIN B4 [get_ports {tx_p}]
set_property PACKAGE_PIN A4 [get_ports {tx_n}]
set_property PACKAGE_PIN B8 [get_ports {rx_p}]
set_property PACKAGE_PIN A8 [get_ports {rx_n}]
