(module
  ;; Sahi WebAssembly (WAT) Zero-Copy 64-Byte Wire Frame Decoder for web.sahi.com
  ;; Reads SahiWireFrame64 directly from shared linear memory at offset $ptr in <80ns
  (memory (export "memory") 1)

  ;; Verify magic bytes 0x53414849 ("SAHI") at offset 0
  (func (export "verify_sahi_magic") (param $ptr i32) (result i32)
    (i32.eq
      (i32.load (local.get $ptr))
      (i32.const 0x53414849)
    )
  )

  ;; Read calibrated Spot LTP (f64 at byte offset +16)
  (func (export "read_spot_ltp") (param $ptr i32) (result f64)
    (f64.load offset=16 (local.get $ptr))
  )

  ;; Read Zero-Gamma Flip S* (f64 at byte offset +24)
  (func (export "read_zero_gamma_flip") (param $ptr i32) (result f64)
    (f64.load offset=24 (local.get $ptr))
  )

  ;; Read Net Dealer GEX in Crores (f64 at byte offset +32)
  (func (export "read_net_dealer_gex") (param $ptr i32) (result f64)
    (f64.load offset=32 (local.get $ptr))
  )

  ;; Read TiltGuard RMS Bitmask (u8 at byte offset +56)
  (func (export "read_tiltguard_bitmask") (param $ptr i32) (result i32)
    (i32.load8_u offset=56 (local.get $ptr))
  )
)
