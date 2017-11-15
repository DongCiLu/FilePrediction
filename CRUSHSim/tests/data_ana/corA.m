function y = corA(x)

%PONLINE - autocorrelation of each traces
%
%Syntax: y = corA(x)
%
%Inputs: x is the trace statistics file
%
%Outputs: y - the autocorrelation of each trace 
%

%Author: Zheng Lu
%Studentid: 000384662
%email: zlu12@utk.edu

N = size(x);
for i = 1:N
    y(i,:) = xcorr(x(i,:), 'unbiased');
end
