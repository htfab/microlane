`default_nettype none

module tt_um_microlane_demo (
    input  wire [7:0] ui_in,    // Dedicated inputs
    output wire [7:0] uo_out,   // Dedicated outputs
    input  wire [7:0] uio_in,   // IOs: Input path
    output wire [7:0] uio_out,  // IOs: Output path
    output wire [7:0] uio_oe,   // IOs: Enable path (active high: 0=input, 1=output)
    input  wire       ena,      // always 1 when the design is powered, so you can ignore it
    input  wire       clk,      // clock
    input  wire       rst_n     // reset_n - low to reset
);

reg [4:0] counter;

always @(posedge clk) begin
    if (~rst_n) begin
        counter <= 0;
    end else if(counter < 21) begin
        counter <= counter + 1;
    end else begin
        counter <= 0;
    end
end

reg [7:0] out;

always_comb begin
    case(counter)
         0: out = 8'b01110100; // h
         1: out = 8'b01110111; // A
         2: out = 8'b01010000; // r
         3: out = 8'b01011110; // d
         4: out = 8'b01111001; // E
         5: out = 8'b01010100; // n
         6: out = 8'b01111001; // E
         7: out = 8'b01011110; // d
         8: out = 8'b00000000; //
         9: out = 8'b00111110; // U
        10: out = 8'b01101101; // S
        11: out = 8'b00110000; // I
        12: out = 8'b01010100; // n
        13: out = 8'b00111101; // G
        14: out = 8'b00000000; //
        15: out = 8'b01110011; // P
        16: out = 8'b01101110; // y
        17: out = 8'b01111000; // t
        18: out = 8'b01110100; // h
        19: out = 8'b01011100; // o
        20: out = 8'b01010100; // n
        21: out = 8'b00000000; //
        default: out = 8'b10000000;
    endcase
end

assign uo_out = out;
assign uio_out = 0;
assign uio_oe  = 0;

wire _unused = &{ena, ui_in, uio_in, 1'b0};

endmodule
