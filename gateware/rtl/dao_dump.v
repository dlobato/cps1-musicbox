module dao_dump(
    input  sample,
    input  en,
    input  [15:0] left,
    input  [15:0] right
);

parameter DUMPFILE = "dao.raw";

integer fsnd;
initial begin
    fsnd=$fopen(DUMPFILE,"wb");
end

always @(posedge sample) begin
    if (en) $fwrite(fsnd,"%u", {left, right});
end

endmodule