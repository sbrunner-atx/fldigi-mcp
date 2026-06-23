# fldigi XML-RPC API — Machine-Readable Method Catalog

Field-verified against **fldigi 4.2.11** via `fldigi.list` on 2026-06-23.
Total methods: **174**. Companion to [FLDIGI-API.md](FLDIGI-API.md).

Categories: **read** (returns state, no side effect) · **write** (changes
state / fires an action) · **keying** (puts RF on the air — see transmit safety
in FLDIGI-API.md). Type codes: void, bool, int, double, string, bytes (base64),
array, struct. Confidence: all rows enumerated live (`fldigi.list`).

| Method | Args | Returns | Category | Notes |
| --- | --- | --- | --- | --- |
| `fldigi.list` | — | array | read |  |
| `fldigi.name` | — | string | read |  |
| `fldigi.version_struct` | — | struct | read |  |
| `fldigi.version` | — | string | read |  |
| `fldigi.name_version` | — | string | read |  |
| `fldigi.config_dir` | — | string | read |  |
| `fldigi.terminate` | int | void | write |  |
| `modem.get_mode` | — | string | read |  |
| `modem.get_submode` | — | string | read |  |
| `modem.get_name` | — | string | read |  |
| `modem.get_io_names` | — | array | read |  |
| `modem.get_names` | — | array | read |  |
| `modem.get_id` | — | int | read |  |
| `modem.get_max_id` | — | int | read |  |
| `modem.set_by_name` | string | string | write |  |
| `modem.set_by_id` | int | int | write |  |
| `modem.set_carrier` | int | int | write |  |
| `modem.inc_carrier` | int | int | write |  |
| `modem.get_carrier` | — | int | read |  |
| `modem.get_afc_search_range` | — | int | read |  |
| `modem.set_afc_search_range` | int | int | write |  |
| `modem.inc_afc_search_range` | int | int | write |  |
| `modem.get_bandwidth` | — | int | read |  |
| `modem.set_bandwidth` | int | int | write |  |
| `modem.inc_bandwidth` | int | int | write |  |
| `modem.get_quality` | — | double | read |  |
| `modem.search_up` | — | void | write |  |
| `modem.search_down` | — | void | write |  |
| `modem.olivia.set_bandwidth` | int | void | write |  |
| `modem.olivia.get_bandwidth` | — | int | read |  |
| `modem.olivia.set_tones` | int | void | write |  |
| `modem.olivia.get_tones` | — | int | read |  |
| `main.get_status1` | — | string | read |  |
| `main.get_status2` | — | string | read |  |
| `main.get_sideband` | — | string | read | deprecated |
| `main.set_sideband` | string | void | write | deprecated |
| `main.get_wf_sideband` | — | string | read |  |
| `main.set_wf_sideband` | string | void | write |  |
| `main.get_frequency` | — | double | read | deprecated |
| `main.set_frequency` | double | double | write |  |
| `main.inc_frequency` | double | double | write |  |
| `main.get_afc` | — | bool | read |  |
| `main.set_afc` | bool | bool | write |  |
| `main.toggle_afc` | — | bool | write |  |
| `main.get_squelch` | — | bool | read |  |
| `main.set_squelch` | bool | bool | write |  |
| `main.toggle_squelch` | — | bool | write |  |
| `main.get_squelch_level` | — | double | read |  |
| `main.set_squelch_level` | double | double | write |  |
| `main.inc_squelch_level` | double | double | write |  |
| `main.get_reverse` | — | bool | read |  |
| `main.set_reverse` | bool | bool | write |  |
| `main.toggle_reverse` | — | bool | write |  |
| `main.get_lock` | — | bool | read |  |
| `main.set_lock` | bool | bool | write |  |
| `main.toggle_lock` | — | bool | write |  |
| `main.get_txid` | — | bool | read |  |
| `main.set_txid` | bool | bool | write |  |
| `main.toggle_txid` | — | bool | write |  |
| `main.get_rsid` | — | bool | read |  |
| `main.set_rsid` | bool | bool | write |  |
| `main.toggle_rsid` | — | bool | write |  |
| `main.get_trx_status` | — | string | read |  |
| `main.tx` | — | void | keying |  |
| `main.tune` | — | void | keying |  |
| `main.rsid` | — | void | write | deprecated |
| `main.rx` | — | void | write |  |
| `main.rx_tx` | — | void | write |  |
| `main.rx_only` | — | void | write |  |
| `main.abort` | — | void | write |  |
| `main.get_trx_state` | — | string | read |  |
| `main.get_tx_timing` | string | void | read |  |
| `main.get_char_rates` | — | string | read |  |
| `main.get_char_timing` | int | void | read |  |
| `main.set_rig_name` | string | void | write | deprecated |
| `main.set_rig_frequency` | double | double | write | deprecated |
| `main.set_rig_modes` | array | void | write | deprecated |
| `main.set_rig_mode` | string | void | write | deprecated |
| `main.get_rig_modes` | — | array | read | deprecated |
| `main.get_rig_mode` | — | string | read | deprecated |
| `main.set_rig_bandwidths` | array | void | write | deprecated |
| `main.set_rig_bandwidth` | string | void | write | deprecated |
| `main.get_rig_bandwidth` | — | string | read | deprecated |
| `main.get_rig_bandwidths` | array | void | read | deprecated |
| `main.run_macro` | int | void | keying |  |
| `main.get_max_macro_id` | — | int | read |  |
| `rig.set_name` | string | void | write |  |
| `rig.get_name` | — | string | read |  |
| `rig.set_frequency` | double | double | write |  |
| `rig.set_smeter` | int | void | write |  |
| `rig.set_pwrmeter` | int | void | write |  |
| `rig.set_modes` | array | void | write |  |
| `rig.set_mode` | string | void | write |  |
| `rig.get_modes` | — | array | read |  |
| `rig.get_mode` | — | string | read |  |
| `rig.set_bandwidths` | array | void | write |  |
| `rig.set_bandwidth` | string | void | write |  |
| `rig.get_frequency` | — | double | read |  |
| `rig.get_bandwidth` | — | string | read |  |
| `rig.get_bandwidths` | — | array | read |  |
| `rig.get_notch` | — | string | read |  |
| `rig.set_notch` | int | void | write |  |
| `rig.enable_qsy` | int | void | write |  |
| `log.get_frequency` | — | string | read |  |
| `log.get_time_on` | — | string | read |  |
| `log.get_time_off` | — | string | read |  |
| `log.get_date_on` | — | string | read |  |
| `log.get_date_off` | — | string | read |  |
| `log.get_call` | — | string | read |  |
| `log.get_name` | — | string | read |  |
| `log.get_rst_in` | — | string | read |  |
| `log.get_rst_out` | — | string | read |  |
| `log.set_rst_in` | string | void | write |  |
| `log.set_rst_out` | string | void | write |  |
| `log.get_serial_number` | — | string | read |  |
| `log.get_serial_number_sent` | — | string | read |  |
| `log.get_exchange` | — | string | read |  |
| `log.set_exchange` | string | void | write |  |
| `log.get_state` | — | string | read |  |
| `log.get_province` | — | string | read |  |
| `log.get_country` | — | string | read |  |
| `log.get_qth` | — | string | read |  |
| `log.get_band` | — | string | read |  |
| `log.get_sideband` | — | string | read | deprecated |
| `log.get_notes` | — | string | read |  |
| `log.get_locator` | — | string | read |  |
| `log.get_az` | — | string | read |  |
| `log.clear` | — | void | write |  |
| `log.set_call` | string | void | write |  |
| `log.set_name` | string | void | write |  |
| `log.set_qth` | string | void | write |  |
| `log.set_locator` | string | void | write |  |
| `log.set_serial_number` | string | void | write |  |
| `log.set_contest_counter` | string | void | write |  |
| `logbook.last_record` | — | string | read |  |
| `logbook.all_records` | — | string | read |  |
| `main.flmsg_online` | — | void | write |  |
| `main.flmsg_available` | — | void | write |  |
| `main.flmsg_transfer` | — | void | write |  |
| `main.flmsg_squelch` | — | bool | write |  |
| `flmsg.online` | — | void | write |  |
| `flmsg.available` | — | void | write |  |
| `flmsg.transfer` | — | void | write |  |
| `flmsg.squelch` | — | bool | read |  |
| `flmsg.get_data` | — | bytes | read |  |
| `io.in_use` | — | string | read |  |
| `io.enable_kiss` | — | void | write |  |
| `io.enable_arq` | — | void | write |  |
| `text.get_rx_length` | — | int | read |  |
| `text.get_rx` | int int | bytes | read |  |
| `text.clear_rx` | — | void | write |  |
| `text.add_tx` | string | void | write |  |
| `text.add_tx_queu` | string | void | write |  |
| `text.add_tx_bytes` | bytes | void | write |  |
| `text.clear_tx` | — | void | write |  |
| `rxtx.get_data` | — | bytes | read |  |
| `rx.get_data` | — | bytes | read |  |
| `tx.get_data` | — | bytes | read |  |
| `spot.get_auto` | — | bool | read |  |
| `spot.set_auto` | bool | bool | write |  |
| `spot.toggle_auto` | — | bool | write |  |
| `spot.pskrep.get_count` | — | int | read |  |
| `wefax.state_string` | — | string | read |  |
| `wefax.skip_apt` | — | string | write |  |
| `wefax.skip_phasing` | — | string | write |  |
| `wefax.set_tx_abort_flag` | — | string | write |  |
| `wefax.end_reception` | — | string | write |  |
| `wefax.start_manual_reception` | — | string | write |  |
| `wefax.set_adif_log` | bool | string | write |  |
| `wefax.set_max_lines` | int | string | write |  |
| `wefax.get_received_file` | int | string | read |  |
| `wefax.send_file` | string int | string | keying |  |
| `navtex.get_message` | int | string | read |  |
| `navtex.send_message` | string | string | keying |  |
