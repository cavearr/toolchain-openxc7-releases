# The ports on pads of bank 14 (HR), LVCMOS18, from the package_pins.csv of the database.
set_property -dict { PACKAGE_PIN N15 IOSTANDARD LVCMOS18 } [get_ports {clk}]
set_property -dict { PACKAGE_PIN K18 IOSTANDARD LVCMOS18 } [get_ports {d[0]}]
set_property -dict { PACKAGE_PIN K17 IOSTANDARD LVCMOS18 } [get_ports {d[1]}]
set_property -dict { PACKAGE_PIN M14 IOSTANDARD LVCMOS18 } [get_ports {d[2]}]
set_property -dict { PACKAGE_PIN L14 IOSTANDARD LVCMOS18 } [get_ports {d[3]}]
set_property -dict { PACKAGE_PIN L16 IOSTANDARD LVCMOS18 } [get_ports {dq0}]
set_property -dict { PACKAGE_PIN L15 IOSTANDARD LVCMOS18 } [get_ports {cap}]
