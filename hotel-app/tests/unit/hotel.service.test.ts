import { HotelRepository } from '../../src/repository/hotel.repository';
import { HotelService, BookingInput } from '../../src/services/hotel.service';

describe('HotelService', () => {
  let repository: HotelRepository;
  let service: HotelService;
  let roomId: string;

  const CHECK_IN = new Date('2025-12-10T14:00:00.000Z');
  const CHECK_OUT = new Date('2025-12-13T10:00:00.000Z'); // 3 nights

  const BUILD_BOOKING = (overrides: Partial<BookingInput> = {}): BookingInput => ({
    guestId: 'guest_001',
    roomId,
    checkIn: CHECK_IN,
    checkOut: CHECK_OUT,
    ...overrides,
  });

  beforeEach(async () => {
    repository = new HotelRepository();
    service = new HotelService(repository);
    const room = await repository.createRoom({
      number: '201',
      type: 'DOUBLE',
      pricePerNight: 200,
      available: true,
    });
    roomId = room.id;
  });

  afterEach(async () => {
    await repository.clear();
  });

  // --- calculateNights ---
  describe('calculateNights', () => {
    it('should return the correct number of nights', () => {
      const nights = service.calculateNights(CHECK_IN, CHECK_OUT);
      expect(nights).toBe(3);
    });

    it('should throw if checkOut is not after checkIn', () => {
      expect(() => service.calculateNights(CHECK_OUT, CHECK_IN)).toThrow('at least 1 night');
    });

    it('should throw if same day check-in and check-out', () => {
      expect(() => service.calculateNights(CHECK_IN, CHECK_IN)).toThrow('at least 1 night');
    });
  });

  // --- calculateCleaningFee ---
  describe('calculateCleaningFee', () => {
    it('should return 30 for SINGLE rooms', () => {
      expect(service.calculateCleaningFee('SINGLE')).toBe(30);
    });
    it('should return 50 for DOUBLE rooms', () => {
      expect(service.calculateCleaningFee('DOUBLE')).toBe(50);
    });
    it('should return 80 for SUITE rooms', () => {
      expect(service.calculateCleaningFee('SUITE')).toBe(80);
    });
  });

  // --- calculateRefund ---
  describe('calculateRefund', () => {
    let bookingRecord: Awaited<ReturnType<typeof repository.createBooking>>;

    beforeEach(async () => {
      bookingRecord = await repository.createBooking({
        guestId: 'guest_001',
        roomId,
        checkIn: new Date('2025-12-10T14:00:00.000Z'),
        checkOut: new Date('2025-12-13T10:00:00.000Z'),
        nights: 3,
        baseRate: 600,
        cleaningFee: 50,
        total: 650,
      });
    });

    it('should refund 100% when cancelled more than 48h before check-in', () => {
      const cancellationDate = new Date('2025-12-07T00:00:00.000Z'); // ~72h before
      const refund = service.calculateRefund(bookingRecord, cancellationDate);
      expect(refund).toBe(650);
    });

    it('should refund 50% when cancelled between 24h and 48h before check-in', () => {
      const cancellationDate = new Date('2025-12-09T10:00:00.000Z'); // ~28h before
      const refund = service.calculateRefund(bookingRecord, cancellationDate);
      expect(refund).toBe(325);
    });

    it('should refund 0% when cancelled less than 24h before check-in', () => {
      const cancellationDate = new Date('2025-12-10T06:00:00.000Z'); // ~8h before
      const refund = service.calculateRefund(bookingRecord, cancellationDate);
      expect(refund).toBe(0);
    });
  });

  // --- validateBookingInput ---
  describe('validateBookingInput', () => {
    it('should throw when guestId is missing', async () => {
      await expect(service.validateBookingInput(BUILD_BOOKING({ guestId: '' }))).rejects.toThrow('Guest ID is required');
    });

    it('should throw when roomId is missing', async () => {
      await expect(service.validateBookingInput(BUILD_BOOKING({ roomId: '' }))).rejects.toThrow('Room ID is required');
    });

    it('should throw when room does not exist', async () => {
      await expect(service.validateBookingInput(BUILD_BOOKING({ roomId: 'nonexistent' }))).rejects.toThrow('not found');
    });

    it('should throw when room is not available', async () => {
      await repository.updateRoomAvailability(roomId, false);
      await expect(service.validateBookingInput(BUILD_BOOKING())).rejects.toThrow('not available');
    });

    it('should throw when checkOut is before checkIn', async () => {
      await expect(
        service.validateBookingInput(BUILD_BOOKING({ checkIn: CHECK_OUT, checkOut: CHECK_IN }))
      ).rejects.toThrow('at least 1 night');
    });
  });

  // --- createBooking ---
  describe('createBooking', () => {
    it('should create a booking with correct fee calculations for DOUBLE room', async () => {
      const result = await service.createBooking(BUILD_BOOKING());
      expect(result.success).toBe(true);
      expect(result.bookingId).toBeDefined();
      expect(result.nights).toBe(3);
      expect(result.baseRate).toBe(600);    // 3 * 200
      expect(result.cleaningFee).toBe(50);  // DOUBLE
      expect(result.total).toBe(650);
    });

    it('should mark the room as unavailable after booking', async () => {
      await service.createBooking(BUILD_BOOKING());
      const room = await repository.findRoomById(roomId);
      expect(room?.available).toBe(false);
    });

    it('should fail when room is not available', async () => {
      await repository.updateRoomAvailability(roomId, false);
      await expect(service.createBooking(BUILD_BOOKING())).rejects.toThrow('not available');
    });
  });

  // --- cancelBooking ---
  describe('cancelBooking', () => {
    let bookingId: string;

    beforeEach(async () => {
      const result = await service.createBooking(BUILD_BOOKING());
      bookingId = result.bookingId!;
    });

    it('should cancel and refund 100% when cancelled >48h in advance', async () => {
      const cancellationDate = new Date('2025-12-07T00:00:00.000Z');
      const result = await service.cancelBooking(bookingId, cancellationDate);
      expect(result.success).toBe(true);
      expect(result.refundPercentage).toBe(100);
      expect(result.refundAmount).toBe(650);
    });

    it('should cancel and refund 50% when cancelled 24h-48h in advance', async () => {
      const cancellationDate = new Date('2025-12-09T10:00:00.000Z');
      const result = await service.cancelBooking(bookingId, cancellationDate);
      expect(result.success).toBe(true);
      expect(result.refundPercentage).toBe(50);
    });

    it('should cancel and refund 0% when cancelled <24h in advance', async () => {
      const cancellationDate = new Date('2025-12-10T06:00:00.000Z');
      const result = await service.cancelBooking(bookingId, cancellationDate);
      expect(result.success).toBe(true);
      expect(result.refundAmount).toBe(0);
      expect(result.refundPercentage).toBe(0);
    });

    it('should make the room available again after cancellation', async () => {
      await service.cancelBooking(bookingId, new Date('2025-12-07T00:00:00.000Z'));
      const room = await repository.findRoomById(roomId);
      expect(room?.available).toBe(true);
    });

    it('should fail when booking is not found', async () => {
      const result = await service.cancelBooking('bad_id', new Date());
      expect(result.success).toBe(false);
      expect(result.errorMessage).toContain('not found');
    });

    it('should fail when booking is already cancelled', async () => {
      await service.cancelBooking(bookingId, new Date('2025-12-07T00:00:00.000Z'));
      const result = await service.cancelBooking(bookingId, new Date('2025-12-07T00:00:00.000Z'));
      expect(result.success).toBe(false);
      expect(result.errorMessage).toContain('already cancelled');
    });

    it('should fail when booking is completed', async () => {
      await repository.updateBookingStatus(bookingId, 'COMPLETED');
      const result = await service.cancelBooking(bookingId, new Date());
      expect(result.success).toBe(false);
      expect(result.errorMessage).toContain('Completed');
    });
  });

  // --- getBooking ---
  describe('getBooking', () => {
    it('should return the booking when it exists', async () => {
      const created = await service.createBooking(BUILD_BOOKING());
      const booking = await service.getBooking(created.bookingId!);
      expect(booking).not.toBeNull();
      expect(booking?.id).toBe(created.bookingId);
    });

    it('should return null when booking does not exist', async () => {
      const booking = await service.getBooking('nonexistent');
      expect(booking).toBeNull();
    });
  });
});
